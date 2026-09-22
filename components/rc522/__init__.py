from esphome import automation, pins
import esphome.codegen as cg
from esphome.components import i2c
import esphome.config_validation as cv
from esphome.const import (
    CONF_ON_TAG,
    CONF_ON_TAG_REMOVED,
    CONF_RESET_PIN,
    CONF_TRIGGER_ID,
)

# Forked from the ESPHome 2026.8.2 built-in `rc522` component (see rc522.h for why).
CODEOWNERS = ["@glmnet"]
AUTO_LOAD = ["binary_sensor", "nfc"]

CONF_RC522_ID = "rc522_id"
CONF_TAG_LOST_THRESHOLD = "tag_lost_threshold"

rc522_ns = cg.esphome_ns.namespace("rc522")
RC522 = rc522_ns.class_("RC522", cg.PollingComponent, i2c.I2CDevice)
RC522Trigger = rc522_ns.class_(
    "RC522Trigger", automation.Trigger.template(cg.std_string, cg.std_string)
)

RC522_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(RC522),
        cv.Optional(CONF_RESET_PIN): pins.gpio_output_pin_schema,
        cv.Optional(CONF_ON_TAG): automation.validate_automation(
            {
                cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(RC522Trigger),
            }
        ),
        cv.Optional(CONF_ON_TAG_REMOVED): automation.validate_automation(
            {
                cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(RC522Trigger),
            }
        ),
        # Consecutive missed polls required before a present tag is declared removed. Filters
        # out single-poll read flickers that would otherwise fire a spurious on_tag_removed
        # immediately followed by a re-fired on_tag (e.g. restarting album playback in HA).
        cv.Optional(CONF_TAG_LOST_THRESHOLD, default=3): cv.int_range(min=1, max=20),
    }
).extend(cv.polling_component_schema("1s"))


async def setup_rc522(var, config):
    await cg.register_component(var, config)

    if CONF_RESET_PIN in config:
        reset = await cg.gpio_pin_expression(config[CONF_RESET_PIN])
        cg.add(var.set_reset_pin(reset))

    cg.add(var.set_tag_lost_threshold(config[CONF_TAG_LOST_THRESHOLD]))

    for conf in config.get(CONF_ON_TAG, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID])
        cg.add(var.register_ontag_trigger(trigger))
        # x = tag UID (hex string, as before), y = decoded NDEF URI payload, or "" if none found.
        await automation.build_automation(
            trigger, [(cg.std_string, "x"), (cg.std_string, "y")], conf
        )

    for conf in config.get(CONF_ON_TAG_REMOVED, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID])
        cg.add(var.register_ontagremoved_trigger(trigger))
        # y is always "" for tag removal.
        await automation.build_automation(
            trigger, [(cg.std_string, "x"), (cg.std_string, "y")], conf
        )
