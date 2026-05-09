#include "safety.h"

bool tilt_within_mechanical_limits(float tilt_deg) {
    return tilt_deg >= CC_TILT_MIN_DEG && tilt_deg <= CC_TILT_MAX_DEG;
}

float clamp_tilt_to_mechanical_limits(float tilt_deg) {
    if (tilt_deg < CC_TILT_MIN_DEG) {
        return CC_TILT_MIN_DEG;
    }
    if (tilt_deg > CC_TILT_MAX_DEG) {
        return CC_TILT_MAX_DEG;
    }
    return tilt_deg;
}
