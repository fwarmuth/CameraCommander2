#include <Arduino.h>

#include "GearedStepper.h"
#include "protocol.h"
#include "safety.h"

#if defined(ESP8266)
#define TT_STEP_PIN D4
#define TT_DIR_PIN D5
#define TT_ENABLE_PIN D0
#define VT_STEP_PIN D6
#define VT_DIR_PIN D7
#define VT_ENABLE_PIN D8
#define MS1_PIN D1
#define MS2_PIN D2
#define MS3_PIN D3
#else
#define TT_STEP_PIN 16
#define TT_DIR_PIN 17
#define TT_ENABLE_PIN 18
#define VT_STEP_PIN 19
#define VT_DIR_PIN 21
#define VT_ENABLE_PIN 22
#define MS1_PIN 23
#define MS2_PIN 25
#define MS3_PIN 26
#endif

constexpr long MOTOR_STEPS_PER_REV = 200;
constexpr float GEAR_RATIO_TT = 11.335f;
constexpr float GEAR_RATIO_VT = 6.2f * 7.5f;
constexpr float RATIO_TT_TO_VT = GEAR_RATIO_VT / GEAR_RATIO_TT;
constexpr float ROT_SPEED0 = 150.0f;
constexpr float ROT_ACCEL0 = 80.0f;
constexpr unsigned long SETTLE_DELAY_MS = 250;
constexpr unsigned long PROGRESS_INTERVAL_MS = 200;

GearedStepper turntableStepper(
    TT_STEP_PIN, TT_DIR_PIN, TT_ENABLE_PIN,
    MS1_PIN, MS2_PIN, MS3_PIN,
    MOTOR_STEPS_PER_REV, GEAR_RATIO_TT);

GearedStepper tiltStepper(
    VT_STEP_PIN, VT_DIR_PIN, VT_ENABLE_PIN,
    MS1_PIN, MS2_PIN, MS3_PIN,
    MOTOR_STEPS_PER_REV, GEAR_RATIO_VT);

struct Axis {
    GearedStepper& stepper;
    int direction = 1;
};

Axis rot{turntableStepper};
Axis til{tiltStepper};
float gRotSpeed = ROT_SPEED0;
float gRotAccel = ROT_ACCEL0;
bool gDriversEnabled = true;

enum class MotionState {
    Idle,
    Moving,
    Settling
};

MotionState gMotionState = MotionState::Idle;
unsigned long gLastProgressMs = 0;
unsigned long gSettleStartedMs = 0;

void ack(const char* message) {
    Serial.println(message);
}

void ack(const String& message) {
    Serial.println(message);
}

long deg_to_microsteps(GearedStepper& stepper, float deg) {
    const long steps_per_rev =
        stepper.getOutputStepsPerRotation() * stepper.getMicrostepResolution();
    return lroundf(deg / 360.0f * static_cast<float>(steps_per_rev));
}

float microsteps_to_deg(const GearedStepper& stepper, long steps) {
    const long steps_per_rev =
        stepper.getOutputStepsPerRotation() * stepper.getMicrostepResolution();
    if (steps_per_rev == 0) {
        return 0.0f;
    }
    return static_cast<float>(steps) * 360.0f / static_cast<float>(steps_per_rev);
}

void set_rotary_motor_speed(float speed, float acceleration) {
    turntableStepper.setMaxSpeed(speed);
    turntableStepper.setAcceleration(acceleration);
    tiltStepper.setMaxSpeed(speed * RATIO_TT_TO_VT);
    tiltStepper.setAcceleration(acceleration * RATIO_TT_TO_VT);
}

void zero_position() {
    turntableStepper.setCurrentPosition(0);
    turntableStepper.moveTo(0);
    tiltStepper.setCurrentPosition(0);
    tiltStepper.moveTo(0);
}

void set_drivers(bool enabled) {
    if (enabled) {
        turntableStepper.enable();
        tiltStepper.enable();
        gDriversEnabled = true;
        zero_position();
        ack("OK DRIVERS ON");
        return;
    }
    turntableStepper.disable();
    tiltStepper.disable();
    gDriversEnabled = false;
    zero_position();
    ack("OK DRIVERS OFF");
}

float estimate_move_duration(float pan_deg, float tilt_deg) {
    const float current_pan = microsteps_to_deg(turntableStepper, turntableStepper.currentPosition());
    const float current_tilt = microsteps_to_deg(tiltStepper, tiltStepper.currentPosition());
    
    const float delta_pan = abs(pan_deg - current_pan);
    const float delta_tilt = abs(tilt_deg - current_tilt);
    
    // Very simplified estimate: distance / maxSpeed
    // AccelStepper speed is steps/s.
    const float pan_steps_per_deg = static_cast<float>(turntableStepper.getOutputStepsPerRotation() * turntableStepper.getMicrostepResolution()) / 360.0f;
    const float tilt_steps_per_deg = static_cast<float>(tiltStepper.getOutputStepsPerRotation() * tiltStepper.getMicrostepResolution()) / 360.0f;
    
    const float pan_time = (delta_pan * pan_steps_per_deg) / turntableStepper.maxSpeed();
    const float tilt_time = (delta_tilt * tilt_steps_per_deg) / tiltStepper.maxSpeed();
    
    return max(pan_time, tilt_time);
}

void move_absolute(float pan_deg, float tilt_deg) {
    if (!gDriversEnabled) {
        ack(cc_protocol::REPLY_ERR_DRIVERS_DISABLED);
        return;
    }

    const float safe_tilt = clamp_tilt_to_mechanical_limits(tilt_deg);
    const long target_pan = deg_to_microsteps(turntableStepper, pan_deg);
    const long target_tilt = deg_to_microsteps(tiltStepper, safe_tilt);

    if (turntableStepper.currentPosition() == target_pan && 
        tiltStepper.currentPosition() == target_tilt) {
        ack(cc_protocol::REPLY_ERR_ALREADY_AT_TARGET);
        return;
    }

    const float duration = estimate_move_duration(pan_deg, safe_tilt);
    ack(String(cc_protocol::REPLY_ESTIMATE) + " " + String(duration, 2));

    turntableStepper.moveTo(target_pan);
    tiltStepper.moveTo(target_tilt);
    gMotionState = MotionState::Moving;
    gLastProgressMs = millis();
}

void report_status() {
    const float pan_deg =
        microsteps_to_deg(turntableStepper, turntableStepper.currentPosition());
    const float tilt_deg = microsteps_to_deg(tiltStepper, tiltStepper.currentPosition());
    ack(String("STATUS ") + String(pan_deg, 3) + " " + String(tilt_deg, 3) + " " +
        (gDriversEnabled ? "1" : "0"));
}

void report_progress() {
    const float pan_deg =
        microsteps_to_deg(turntableStepper, turntableStepper.currentPosition());
    const float tilt_deg = microsteps_to_deg(tiltStepper, tiltStepper.currentPosition());
    ack(String(cc_protocol::REPLY_PROGRESS) + " " + String(pan_deg, 3) + " " + String(tilt_deg, 3));
}

void print_banner() {
    Serial.println(F("Dual-axis turntable - firmware " FW_VERSION));
    Serial.println(F("V | M <pan> <tilt> | S | 1/2/4/8/6 | n/c/r/x | w/p/t/z | X | +/- | d/e"));
}

void setup() {
    Serial.begin(9600);
    delay(200);

    rot.stepper.begin();
    til.stepper.begin();
    zero_position();
    set_rotary_motor_speed(gRotSpeed, gRotAccel);
    gDriversEnabled = true;

    print_banner();
}

void dispatch(const cc_protocol::ParsedCommand& command) {
    using cc_protocol::CommandKind;
    switch (command.kind) {
        case CommandKind::Empty:
            return;
        case CommandKind::SyntaxError:
            ack(cc_protocol::REPLY_ERR_SYNTAX);
            return;
        case CommandKind::Unknown:
            ack(cc_protocol::REPLY_ERR_UNKNOWN);
            return;
        case CommandKind::Version:
            ack(String("VERSION ") + FW_VERSION);
            return;
        case CommandKind::Move:
            move_absolute(command.pan_deg, command.tilt_deg);
            return;
        case CommandKind::Status:
            report_status();
            return;
        case CommandKind::Microstep:
            turntableStepper.setMicrostepResolution(command.microstep);
            tiltStepper.setMicrostepResolution(command.microstep);
            ack(String("OK MICROSTEP ") + command.microstep);
            return;
        case CommandKind::PanStep:
            rot.stepper.move(rot.direction);
            ack("OK ROT STEP");
            return;
        case CommandKind::PanRevolution:
            rot.stepper.move(rot.direction * rot.stepper.getOutputStepsPerRotation() *
                             rot.stepper.getMicrostepResolution());
            ack("OK ROT REV");
            return;
        case CommandKind::PanDirection:
            rot.direction = -rot.direction;
            ack("OK ROT DIR");
            return;
        case CommandKind::PanStop:
            rot.stepper.stop();
            ack("OK ROT STOP");
            return;
        case CommandKind::TiltStep:
            til.stepper.move(til.direction);
            ack("OK TILT STEP");
            return;
        case CommandKind::TiltRevolution:
            til.stepper.move(til.direction * til.stepper.getOutputStepsPerRotation() *
                             til.stepper.getMicrostepResolution());
            ack("OK TILT REV");
            return;
        case CommandKind::TiltDirection:
            til.direction = -til.direction;
            ack("OK TILT DIR");
            return;
        case CommandKind::TiltStop:
            til.stepper.stop();
            ack("OK TILT STOP");
            return;
        case CommandKind::GlobalStop:
            rot.stepper.stop();
            til.stepper.stop();
            gMotionState = MotionState::Idle;
            ack("OK STOP");
            return;
        case CommandKind::SpeedUp:
        case CommandKind::SpeedDown: {
            const float factor = command.kind == CommandKind::SpeedUp ? 1.10f : 0.90f;
            gRotSpeed *= factor;
            gRotAccel *= factor;
            set_rotary_motor_speed(gRotSpeed, gRotAccel);
            ack("OK SPEED");
            return;
        }
        case CommandKind::DriversOff:
            set_drivers(false);
            return;
        case CommandKind::DriversOn:
            set_drivers(true);
            return;
    }
}

void loop() {
    turntableStepper.run();
    tiltStepper.run();

    if (gMotionState == MotionState::Moving) {
        if (turntableStepper.distanceToGo() == 0 && tiltStepper.distanceToGo() == 0) {
            gMotionState = MotionState::Settling;
            gSettleStartedMs = millis();
        } else if (millis() - gLastProgressMs >= PROGRESS_INTERVAL_MS) {
            report_progress();
            gLastProgressMs = millis();
        }
    } else if (gMotionState == MotionState::Settling) {
        if (millis() - gSettleStartedMs >= SETTLE_DELAY_MS) {
            gMotionState = MotionState::Idle;
            ack(cc_protocol::REPLY_DONE);
        }
    }

    if (!Serial.available()) {
        return;
    }

    String line = Serial.readStringUntil('\n');
    line.trim();
    dispatch(cc_protocol::parse_command(line.c_str()));
}
