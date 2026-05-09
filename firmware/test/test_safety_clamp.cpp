#include <unity.h>

#include "../src/safety.h"

void test_tilt_limit_accepts_inside_window() {
    TEST_ASSERT_TRUE(tilt_within_mechanical_limits(0.0f));
    TEST_ASSERT_TRUE(tilt_within_mechanical_limits(CC_TILT_MIN_DEG));
    TEST_ASSERT_TRUE(tilt_within_mechanical_limits(CC_TILT_MAX_DEG));
}

void test_tilt_limit_rejects_outside_window() {
    TEST_ASSERT_FALSE(tilt_within_mechanical_limits(CC_TILT_MIN_DEG - 0.1f));
    TEST_ASSERT_FALSE(tilt_within_mechanical_limits(CC_TILT_MAX_DEG + 0.1f));
}

void test_clamp_limits_tilt() {
    TEST_ASSERT_EQUAL_FLOAT(CC_TILT_MIN_DEG, clamp_tilt_to_mechanical_limits(CC_TILT_MIN_DEG - 1.0f));
    TEST_ASSERT_EQUAL_FLOAT(CC_TILT_MAX_DEG, clamp_tilt_to_mechanical_limits(CC_TILT_MAX_DEG + 1.0f));
    TEST_ASSERT_EQUAL_FLOAT(12.0f, clamp_tilt_to_mechanical_limits(12.0f));
}

int main() {
    UNITY_BEGIN();
    RUN_TEST(test_tilt_limit_accepts_inside_window);
    RUN_TEST(test_tilt_limit_rejects_outside_window);
    RUN_TEST(test_clamp_limits_tilt);
    return UNITY_END();
}
