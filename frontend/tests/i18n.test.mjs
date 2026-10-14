import assert from "node:assert/strict";
import test from "node:test";

import {
  copyKeys,
  isLocale,
  localeTag,
  localizeMessage,
  locales,
  translate,
} from "../app/platform/i18n.ts";

test("platform copy has a nonempty Hindi translation for every catalog key", () => {
  assert.deepEqual(locales, ["en", "hi"]);
  assert.equal(new Set(copyKeys).size, copyKeys.length);
  for (const key of copyKeys) {
    assert.equal(translate("en", key), key);
    assert.ok(translate("hi", key).trim(), `Missing Hindi copy for ${key}`);
  }
});

test("locale preference and localized API messages fall back safely", () => {
  assert.equal(isLocale("en"), true);
  assert.equal(isLocale("hi"), true);
  assert.equal(isLocale("fr"), false);
  assert.equal(isLocale(null), false);
  assert.equal(localeTag("en"), "en-US");
  assert.equal(localeTag("hi"), "hi-IN");
  assert.equal(
    localizeMessage("hi", "Saved. Your workspace is up to date."),
    "सहेजा गया। आपका कार्यक्षेत्र नवीनतम है।",
  );
  assert.equal(localizeMessage("hi", "An unknown server message."), "An unknown server message.");
});
