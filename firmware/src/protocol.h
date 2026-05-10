#ifndef CAMERACOMMANDER_PROTOCOL_H
#define CAMERACOMMANDER_PROTOCOL_H

#include <cctype>
#include <cstdlib>
#include <cstring>

#define FW_VERSION "1.1.0"

namespace cc_protocol {

constexpr char REPLY_DONE[] = "DONE";
constexpr char REPLY_ESTIMATE[] = "ESTIMATE";
constexpr char REPLY_PROGRESS[] = "PROGRESS";
constexpr char REPLY_ERR_SYNTAX[] = "ERR Syntax";
constexpr char REPLY_ERR_UNKNOWN[] = "ERR Unknown";
constexpr char REPLY_ERR_DRIVERS_DISABLED[] = "ERR DRIVERS_DISABLED";
constexpr char REPLY_ERR_ALREADY_AT_TARGET[] = "ERR AlreadyAtTarget";
constexpr char REPLY_ERR_MOTOR_STALL[] = "ERR MotorStall";

enum class CommandKind {
    Empty,
    Version,
    Move,
    Status,
    Microstep,
    PanStep,
    PanRevolution,
    PanDirection,
    PanStop,
    TiltStep,
    TiltRevolution,
    TiltDirection,
    TiltStop,
    GlobalStop,
    SpeedUp,
    SpeedDown,
    DriversOff,
    DriversOn,
    SyntaxError,
    Unknown,
};

struct ParsedCommand {
    CommandKind kind = CommandKind::Empty;
    float pan_deg = 0.0f;
    float tilt_deg = 0.0f;
    int microstep = 0;
};

inline const char* skip_spaces(const char* value) {
    while (*value != '\0' && std::isspace(static_cast<unsigned char>(*value))) {
        ++value;
    }
    return value;
}

inline bool at_line_end(const char* value) {
    return *skip_spaces(value) == '\0';
}

inline bool parse_float(const char*& cursor, float& out) {
    cursor = skip_spaces(cursor);
    if (*cursor == '\0') {
        return false;
    }
    char* end = nullptr;
    out = std::strtof(cursor, &end);
    if (end == cursor) {
        return false;
    }
    cursor = end;
    return true;
}

inline ParsedCommand parse_command(const char* raw_line) {
    ParsedCommand parsed;
    const char* cursor = skip_spaces(raw_line);
    if (*cursor == '\0') {
        return parsed;
    }

    const char token = *cursor++;
    const char lower = static_cast<char>(std::tolower(static_cast<unsigned char>(token)));

    if (lower == 'm') {
        if (!parse_float(cursor, parsed.pan_deg) || !parse_float(cursor, parsed.tilt_deg) ||
            !at_line_end(cursor)) {
            parsed.kind = CommandKind::SyntaxError;
            return parsed;
        }
        parsed.kind = CommandKind::Move;
        return parsed;
    }

    if (!at_line_end(cursor)) {
        parsed.kind = CommandKind::SyntaxError;
        return parsed;
    }

    if (token == 'X') {
        parsed.kind = CommandKind::GlobalStop;
        return parsed;
    }

    switch (lower) {
        case 'v':
            parsed.kind = CommandKind::Version;
            return parsed;
        case 's':
            parsed.kind = CommandKind::Status;
            return parsed;
        case '1':
        case '2':
        case '4':
        case '8':
            parsed.kind = CommandKind::Microstep;
            parsed.microstep = token - '0';
            return parsed;
        case '6':
            parsed.kind = CommandKind::Microstep;
            parsed.microstep = 16;
            return parsed;
        case 'n':
            parsed.kind = CommandKind::PanStep;
            return parsed;
        case 'c':
            parsed.kind = CommandKind::PanRevolution;
            return parsed;
        case 'r':
            parsed.kind = CommandKind::PanDirection;
            return parsed;
        case 'x':
            parsed.kind = CommandKind::PanStop;
            return parsed;
        case 'w':
            parsed.kind = CommandKind::TiltStep;
            return parsed;
        case 'p':
            parsed.kind = CommandKind::TiltRevolution;
            return parsed;
        case 't':
            parsed.kind = CommandKind::TiltDirection;
            return parsed;
        case 'z':
            parsed.kind = CommandKind::TiltStop;
            return parsed;
        case '+':
            parsed.kind = CommandKind::SpeedUp;
            return parsed;
        case '-':
            parsed.kind = CommandKind::SpeedDown;
            return parsed;
        case 'd':
            parsed.kind = CommandKind::DriversOff;
            return parsed;
        case 'e':
            parsed.kind = CommandKind::DriversOn;
            return parsed;
        default:
            parsed.kind = CommandKind::Unknown;
            return parsed;
    }
}

}  // namespace cc_protocol

#endif  // CAMERACOMMANDER_PROTOCOL_H
