#include <unity.h>

#include "../src/protocol.h"

using cc_protocol::CommandKind;
using cc_protocol::parse_command;

void assert_kind(CommandKind expected, CommandKind actual) {
    TEST_ASSERT_EQUAL_INT(static_cast<int>(expected), static_cast<int>(actual));
}

void test_parse_move() {
    const auto command = parse_command("M 12.5 -3.0");
    assert_kind(CommandKind::Move, command.kind);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 12.5f, command.pan_deg);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, -3.0f, command.tilt_deg);
}

void test_parse_status() {
    const auto command = parse_command("S");
    assert_kind(CommandKind::Status, command.kind);
}

void test_reject_move_wrong_arity() {
    const auto command = parse_command("M 12.5");
    assert_kind(CommandKind::SyntaxError, command.kind);
}

void test_reject_unknown_token() {
    const auto command = parse_command("?");
    assert_kind(CommandKind::Unknown, command.kind);
}

void test_case_insensitive_tokens() {
    assert_kind(CommandKind::Version, parse_command("v").kind);
    assert_kind(CommandKind::PanStep, parse_command("N").kind);
    assert_kind(CommandKind::TiltRevolution, parse_command("P").kind);
    assert_kind(CommandKind::DriversOn, parse_command("E").kind);
}

void test_global_stop_is_distinct_from_pan_stop() {
    assert_kind(CommandKind::GlobalStop, parse_command("X").kind);
    assert_kind(CommandKind::PanStop, parse_command("x").kind);
}

int main() {
    UNITY_BEGIN();
    RUN_TEST(test_parse_move);
    RUN_TEST(test_parse_status);
    RUN_TEST(test_reject_move_wrong_arity);
    RUN_TEST(test_reject_unknown_token);
    RUN_TEST(test_case_insensitive_tokens);
    RUN_TEST(test_global_stop_is_distinct_from_pan_stop);
    return UNITY_END();
}
