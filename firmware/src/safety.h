#ifndef CAMERACOMMANDER_SAFETY_H
#define CAMERACOMMANDER_SAFETY_H

#ifndef CC_TILT_MIN_DEG
#define CC_TILT_MIN_DEG -75.0f
#endif

#ifndef CC_TILT_MAX_DEG
#define CC_TILT_MAX_DEG 75.0f
#endif

bool tilt_within_mechanical_limits(float tilt_deg);
float clamp_tilt_to_mechanical_limits(float tilt_deg);

#endif  // CAMERACOMMANDER_SAFETY_H
