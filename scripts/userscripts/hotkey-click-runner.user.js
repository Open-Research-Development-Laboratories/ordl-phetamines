// ==UserScript==
// @name         Hotkey Click Runner
// @namespace    https://ordl.local/userscripts
// @version      0.1.0
// @description  Save a click plan and advance one browser action at a time with a hotkey.
// @match        *://*/*
// @run-at       document-idle
// @grant        none
// ==/UserScript==

(() => {
  "use strict";

  const PLAN_KEY = "__hotkey_click_runner_plan__";
  const INDEX_KEY = "__hotkey_click_runner_index__";
  const PROFILES_KEY = "__hotkey_click_runner_profiles__";
  const RUNTIME_KEY = "__hotkey_click_runner_runtime__";
  const DIALOG_POLICY_KEY = "__hotkey_click_runner_dialog_policy__";
  const CLICKABLE_SELECTOR =
    'a, button, [role="button"], input[type="button"], input[type="submit"]';
  const TOAST_ID = "__hotkey_click_runner_toast__";
  const HOTKEY = { altKey: true, shiftKey: true, code: "KeyK" };
  const PREVIEW_HOTKEY = { altKey: true, shiftKey: true, code: "KeyJ" };
  const RESET_HOTKEY = { altKey: true, shiftKey: true, code: "KeyR" };
  const STOP_HOTKEY = { altKey: true, shiftKey: true, code: "KeyX" };
  const RISKY_WORDS = ["submit", "confirm", "authorize", "sign", "finalize"];
  const PROFILE_RETRY_DELAY_MS = 700;

  function normalize(value) {
    return String(value ?? "")
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();
  }

  function readStorage(key, fallbackValue) {
    try {
      const raw = window.localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallbackValue;
    } catch (error) {
      console.error("[HotkeyClickRunner] Failed to read storage:", error);
      return fallbackValue;
    }
  }

  function writeStorage(key, value) {
    window.localStorage.setItem(key, JSON.stringify(value));
  }

  function deleteStorage(key) {
    window.localStorage.removeItem(key);
  }

  function getPlan() {
    return readStorage(PLAN_KEY, []);
  }

  function setPlan(plan) {
    if (!Array.isArray(plan)) {
      throw new Error("Plan must be an array.");
    }

    const normalizedPlan = plan.map((step, index) => normalizeStep(step, index));
    writeStorage(PLAN_KEY, normalizedPlan);
    writeStorage(INDEX_KEY, 0);
    showToast(`Saved ${normalizedPlan.length} step(s).`, "info");
    return normalizedPlan;
  }

  function clearPlan() {
    deleteStorage(PLAN_KEY);
    deleteStorage(INDEX_KEY);
    showToast("Cleared plan.", "info");
  }

  function getIndex() {
    const index = Number(readStorage(INDEX_KEY, 0));
    return Number.isFinite(index) && index >= 0 ? index : 0;
  }

  function setIndex(index) {
    writeStorage(INDEX_KEY, Math.max(0, Number(index) || 0));
  }

  function reset() {
    setIndex(0);
    showToast("Reset progress to step 1.", "info");
  }

  function status() {
    const plan = getPlan();
    const index = getIndex();
    const runtime = getRuntime();
    return {
      totalSteps: plan.length,
      currentStepNumber: plan.length ? Math.min(index + 1, plan.length) : 0,
      remainingSteps: Math.max(plan.length - index, 0),
      nextStep: plan[index] || null,
      profiles: getProfiles().map((profile) => ({
        slot: profile.slot,
        label: profile.label,
        steps: profile.steps.length,
      })),
      activeProfile: runtime,
    };
  }

  function normalizeStep(step, index) {
    if (!step || typeof step !== "object") {
      throw new Error(`Step ${index + 1} must be an object.`);
    }

    const type = normalize(step.type || "click");
    const normalizedStep = {
      type,
      label: String(step.label || `Step ${index + 1}`),
      selector: step.selector ? String(step.selector) : "",
      xpath: step.xpath ? String(step.xpath) : "",
      actionText: step.actionText ? String(step.actionText) : "",
      actionTextMode: normalize(step.actionTextMode || "contains"),
      sectionTitle: step.sectionTitle ? String(step.sectionTitle) : "",
      sectionTitleMode: normalize(step.sectionTitleMode || "contains"),
      accountNumber: step.accountNumber ? String(step.accountNumber) : "",
      contextText: step.contextText ? String(step.contextText) : "",
      contextTextMode: normalize(step.contextTextMode || "contains"),
      urlIncludes: step.urlIncludes
        ? Array.isArray(step.urlIncludes)
          ? step.urlIncludes.map(String)
          : [String(step.urlIncludes)]
        : [],
      allowRisky: Boolean(step.allowRisky),
      count: Math.max(1, Number(step.count ?? step.backCount ?? 1) || 1),
      delayMs: Math.max(
        0,
        Number(step.delayMs ?? (type === "wait" ? step.ms : 700) ?? 700) || 0
      ),
      timeoutMs: Math.max(500, Number(step.timeoutMs ?? 12000) || 12000),
      text: step.text ? String(step.text) : "",
      textGone: step.textGone ? String(step.textGone) : "",
      confirmMode: normalize(step.confirmMode ?? step.confirm ?? "prompt"),
      alertMode: normalize(step.alertMode ?? step.alert ?? "prompt"),
    };

    if (
      !["click", "back", "wait", "waitfortext", "dialogpolicy"].includes(
        normalizedStep.type
      )
    ) {
      throw new Error(`Step ${index + 1} has unsupported type.`);
    }

    if (
      normalizedStep.type === "click" &&
      !normalizedStep.selector &&
      !normalizedStep.xpath &&
      !normalizedStep.actionText
    ) {
      throw new Error(
        `Step ${index + 1} needs at least one of selector, xpath, or actionText.`
      );
    }

    if (!["contains", "exact"].includes(normalizedStep.actionTextMode)) {
      throw new Error(`Step ${index + 1} has unsupported actionTextMode.`);
    }

    if (!["contains", "exact"].includes(normalizedStep.sectionTitleMode)) {
      throw new Error(`Step ${index + 1} has unsupported sectionTitleMode.`);
    }

    if (!["contains", "exact"].includes(normalizedStep.contextTextMode)) {
      throw new Error(`Step ${index + 1} has unsupported contextTextMode.`);
    }

    if (
      normalizedStep.type === "waitfortext" &&
      !normalizedStep.text &&
      !normalizedStep.textGone
    ) {
      throw new Error(`Step ${index + 1} must set text or textGone.`);
    }

    if (!["prompt", "accept"].includes(normalizedStep.confirmMode)) {
      throw new Error(`Step ${index + 1} has unsupported confirmMode.`);
    }

    if (!["prompt", "dismiss"].includes(normalizedStep.alertMode)) {
      throw new Error(`Step ${index + 1} has unsupported alertMode.`);
    }

    return normalizedStep;
  }

  function setExpandedPlan(sections, actions) {
    if (!Array.isArray(sections) || !Array.isArray(actions)) {
      throw new Error("setExpandedPlan expects two arrays: sections and actions.");
    }

    const combinedPlan = [];

    sections.forEach((section, sectionIndex) => {
      actions.forEach((action, actionIndex) => {
        combinedPlan.push({
          ...action,
          sectionTitle: action.sectionTitle || section.sectionTitle,
          accountNumber: action.accountNumber || section.accountNumber,
          contextText: action.contextText || section.contextText,
          label:
            action.label ||
            `${section.sectionTitle || section.accountNumber || "Section"} - ${action.actionText || action.selector || action.xpath || `Action ${actionIndex + 1}`}`,
        });
      });
    });

    return setPlan(combinedPlan);
  }

  function normalizeProfile(profile, index) {
    if (!profile || typeof profile !== "object") {
      throw new Error(`Profile ${index + 1} must be an object.`);
    }

    const slot = Number(profile.slot ?? index + 1);
    if (!Number.isInteger(slot) || slot < 1 || slot > 9) {
      throw new Error(`Profile ${index + 1} must have a slot from 1 to 9.`);
    }

    if (!Array.isArray(profile.steps) || !profile.steps.length) {
      throw new Error(`Profile ${index + 1} must include a non-empty steps array.`);
    }

    return {
      slot,
      label: String(profile.label || `Profile ${slot}`),
      steps: profile.steps.map((step, stepIndex) => normalizeStep(step, stepIndex)),
    };
  }

  function getProfiles() {
    return readStorage(PROFILES_KEY, []);
  }

  function setProfiles(profiles) {
    if (!Array.isArray(profiles)) {
      throw new Error("Profiles must be an array.");
    }

    const normalizedProfiles = profiles.map((profile, index) =>
      normalizeProfile(profile, index)
    );
    const usedSlots = new Set();
    normalizedProfiles.forEach((profile) => {
      if (usedSlots.has(profile.slot)) {
        throw new Error(`Duplicate profile slot ${profile.slot}.`);
      }
      usedSlots.add(profile.slot);
    });

    writeStorage(PROFILES_KEY, normalizedProfiles);
    showToast(`Saved ${normalizedProfiles.length} profile(s).`, "info");
    return normalizedProfiles;
  }

  function clearProfiles() {
    deleteStorage(PROFILES_KEY);
    showToast("Cleared profiles.", "info");
  }

  function getRuntime() {
    return readStorage(RUNTIME_KEY, null);
  }

  function setRuntime(runtime) {
    writeStorage(RUNTIME_KEY, runtime);
  }

  function clearRuntime() {
    deleteStorage(RUNTIME_KEY);
  }

  function getDialogPolicy() {
    return readStorage(DIALOG_POLICY_KEY, { confirm: "prompt", alert: "prompt" });
  }

  function normalizeDialogPolicy(policy) {
    const normalizedPolicy = {
      confirm: normalize(policy?.confirm || "prompt"),
      alert: normalize(policy?.alert || "prompt"),
    };

    if (!["prompt", "accept"].includes(normalizedPolicy.confirm)) {
      throw new Error("Unsupported confirm policy.");
    }

    if (!["prompt", "dismiss"].includes(normalizedPolicy.alert)) {
      throw new Error("Unsupported alert policy.");
    }

    return normalizedPolicy;
  }

  function setDialogPolicy(policy) {
    const normalizedPolicy = normalizeDialogPolicy(policy);
    writeStorage(DIALOG_POLICY_KEY, normalizedPolicy);
    showToast(
      `Dialog policy: confirm=${normalizedPolicy.confirm}, alert=${normalizedPolicy.alert}`,
      "info"
    );
    return normalizedPolicy;
  }

  function getText(element) {
    if (!element) {
      return "";
    }

    if (typeof element.innerText === "string" && element.innerText.trim()) {
      return element.innerText;
    }

    if (typeof element.textContent === "string" && element.textContent.trim()) {
      return element.textContent;
    }

    if (typeof element.value === "string" && element.value.trim()) {
      return element.value;
    }

    return "";
  }

  function isVisible(element) {
    if (!element || !(element instanceof Element)) {
      return false;
    }

    const style = window.getComputedStyle(element);
    if (
      style.display === "none" ||
      style.visibility === "hidden" ||
      style.opacity === "0"
    ) {
      return false;
    }

    const rect = element.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  }

  function matchesText(actualText, expectedText, mode) {
    const actual = normalize(actualText);
    const expected = normalize(expectedText);

    if (!expected) {
      return true;
    }

    if (mode === "exact") {
      return actual === expected;
    }

    return actual.includes(expected);
  }

  function firstVisible(elements) {
    return elements.find(isVisible) || null;
  }

  function findBySelector(selector) {
    try {
      return firstVisible(Array.from(document.querySelectorAll(selector)));
    } catch (error) {
      showToast(`Bad selector: ${selector}`, "error");
      console.error("[HotkeyClickRunner] Bad selector:", error);
      return null;
    }
  }

  function findByXPath(xpath) {
    try {
      const results = [];
      const snapshot = document.evaluate(
        xpath,
        document,
        null,
        XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,
        null
      );

      for (let index = 0; index < snapshot.snapshotLength; index += 1) {
        const node = snapshot.snapshotItem(index);
        if (node instanceof Element) {
          results.push(node);
        }
      }

      return firstVisible(results);
    } catch (error) {
      showToast(`Bad XPath: ${xpath}`, "error");
      console.error("[HotkeyClickRunner] Bad XPath:", error);
      return null;
    }
  }

  function matchesCurrentUrl(step) {
    if (!step.urlIncludes.length) {
      return true;
    }

    const url = normalize(window.location.href);
    return step.urlIncludes.some((value) => url.includes(normalize(value)));
  }

  function scoreCandidate(element, step) {
    const elementText = getText(element);

    if (!matchesText(elementText, step.actionText, step.actionTextMode)) {
      return Number.NEGATIVE_INFINITY;
    }

    let bestScore = step.actionTextMode === "exact" ? 100 : 80;
    let depth = 0;

    for (
      let node = element;
      node && node instanceof Element && node !== document.body;
      node = node.parentElement
    ) {
      const contextText = getText(node);
      let score = bestScore - depth;

      if (step.accountNumber && matchesText(contextText, step.accountNumber, "contains")) {
        score += 45;
      }

      if (
        step.sectionTitle &&
        matchesText(contextText, step.sectionTitle, step.sectionTitleMode)
      ) {
        score += 35;
      }

      if (
        step.contextText &&
        matchesText(contextText, step.contextText, step.contextTextMode)
      ) {
        score += 20;
      }

      if (score > bestScore) {
        bestScore = score;
      }

      depth += 1;
    }

    return bestScore;
  }

  function findByText(step) {
    const candidates = Array.from(document.querySelectorAll(CLICKABLE_SELECTOR))
      .filter(isVisible)
      .map((element) => ({
        element,
        score: scoreCandidate(element, step),
      }))
      .filter((item) => Number.isFinite(item.score))
      .sort((left, right) => right.score - left.score);

    return candidates.length ? candidates[0].element : null;
  }

  function findTarget(step) {
    if (!matchesCurrentUrl(step)) {
      return null;
    }

    if (step.selector) {
      const selectorTarget = findBySelector(step.selector);
      if (selectorTarget) {
        return selectorTarget;
      }
    }

    if (step.xpath) {
      const xpathTarget = findByXPath(step.xpath);
      if (xpathTarget) {
        return xpathTarget;
      }
    }

    if (step.actionText) {
      return findByText(step);
    }

    return null;
  }

  function isRisky(element, step) {
    if (step.allowRisky) {
      return false;
    }

    const text = normalize(getText(element));
    return RISKY_WORDS.some((word) => text.includes(word));
  }

  function flashTarget(element, color) {
    const previousOutline = element.style.outline;
    const previousOutlineOffset = element.style.outlineOffset;
    element.style.outline = `3px solid ${color}`;
    element.style.outlineOffset = "2px";
    window.setTimeout(() => {
      element.style.outline = previousOutline;
      element.style.outlineOffset = previousOutlineOffset;
    }, 1200);
  }

  function showToast(message, level) {
    const colors = {
      info: "#2563eb",
      error: "#b91c1c",
      success: "#15803d",
    };
    let toast = document.getElementById(TOAST_ID);

    if (!toast) {
      toast = document.createElement("div");
      toast.id = TOAST_ID;
      toast.style.position = "fixed";
      toast.style.right = "16px";
      toast.style.bottom = "16px";
      toast.style.zIndex = "2147483647";
      toast.style.maxWidth = "360px";
      toast.style.padding = "10px 12px";
      toast.style.borderRadius = "8px";
      toast.style.font = "13px/1.4 Arial, sans-serif";
      toast.style.color = "#ffffff";
      toast.style.boxShadow = "0 10px 28px rgba(0, 0, 0, 0.25)";
      document.body.appendChild(toast);
    }

    toast.textContent = message;
    toast.style.background = colors[level] || colors.info;
    toast.style.opacity = "1";

    window.clearTimeout(showToast.timerId);
    showToast.timerId = window.setTimeout(() => {
      if (toast) {
        toast.style.opacity = "0";
      }
    }, 2800);
  }
  showToast.timerId = 0;

  const originalConfirm = window.confirm.bind(window);
  const originalAlert = window.alert.bind(window);

  window.confirm = function hotkeyClickRunnerConfirm(message) {
    const policy = getDialogPolicy();
    if (policy.confirm === "accept") {
      console.info("[HotkeyClickRunner] Auto-accepted confirm:", message);
      showToast("Auto-accepted browser confirm.", "info");
      return true;
    }
    return originalConfirm(message);
  };

  window.alert = function hotkeyClickRunnerAlert(message) {
    const policy = getDialogPolicy();
    if (policy.alert === "dismiss") {
      console.info("[HotkeyClickRunner] Auto-dismissed alert:", message);
      showToast("Auto-dismissed browser alert.", "info");
      return;
    }
    return originalAlert(message);
  };

  function getProfileBySlot(slot) {
    return getProfiles().find((profile) => profile.slot === slot) || null;
  }

  function scheduleProfileContinue(delayMs) {
    window.clearTimeout(continueProfile.timerId);
    continueProfile.timerId = window.setTimeout(() => {
      continueProfile();
    }, delayMs);
  }

  function advanceRuntime(runtime, delayMs) {
    const nextRuntime = {
      ...runtime,
      stepIndex: runtime.stepIndex + 1,
      stepStartedAt: Date.now(),
      paused: false,
    };
    setRuntime(nextRuntime);
    if (typeof delayMs === "number") {
      scheduleProfileContinue(delayMs);
    }
    return nextRuntime;
  }

  function pauseRuntime(message) {
    const runtime = getRuntime();
    if (!runtime) {
      return null;
    }

    const pausedRuntime = {
      ...runtime,
      paused: true,
      pausedAt: Date.now(),
    };
    setRuntime(pausedRuntime);
    showToast(message, "error");
    return pausedRuntime;
  }

  function stopProfile(message = "Stopped active profile.") {
    window.clearTimeout(continueProfile.timerId);
    clearRuntime();
    writeStorage(DIALOG_POLICY_KEY, { confirm: "prompt", alert: "prompt" });
    showToast(message, "info");
    return null;
  }

  function resumeProfile() {
    const runtime = getRuntime();
    if (!runtime) {
      showToast("No paused profile to resume.", "error");
      return null;
    }

    const profile = getProfileBySlot(runtime.slot);
    if (!profile) {
      clearRuntime();
      showToast("Saved active profile no longer exists.", "error");
      return null;
    }

    const resumedRuntime = {
      ...runtime,
      paused: false,
      pausedAt: null,
      stepStartedAt: Date.now(),
    };
    setRuntime(resumedRuntime);
    showToast(`Resumed ${profile.label}.`, "info");
    scheduleProfileContinue(150);
    return profile;
  }

  function pageText() {
    return normalize(document.body?.innerText || document.body?.textContent || "");
  }

  function pageHasText(text) {
    return pageText().includes(normalize(text));
  }

  function startProfile(slot) {
    const runtime = getRuntime();
    if (runtime && runtime.slot === slot && runtime.paused) {
      return resumeProfile();
    }

    const profile = getProfileBySlot(slot);
    if (!profile) {
      showToast(`No profile saved for ${slot}.`, "error");
      return null;
    }

    setRuntime({
      slot,
      stepIndex: 0,
      stepStartedAt: Date.now(),
      startedAt: Date.now(),
      paused: false,
    });
    writeStorage(DIALOG_POLICY_KEY, { confirm: "prompt", alert: "prompt" });
    showToast(`Started ${profile.label}.`, "info");
    scheduleProfileContinue(150);
    return profile;
  }

  function handleProfileClick(profile, runtime, step) {
    const target = findTarget(step);

    if (!target) {
      if (Date.now() - runtime.stepStartedAt >= step.timeoutMs) {
        pauseRuntime(`Stopped at ${profile.label}: no match for ${step.label}.`);
        return;
      }

      scheduleProfileContinue(PROFILE_RETRY_DELAY_MS);
      return;
    }

    if (isRisky(target, step)) {
      target.scrollIntoView({ block: "center", inline: "center", behavior: "smooth" });
      flashTarget(target, "#b91c1c");
      pauseRuntime(`Blocked risky click for ${step.label}.`);
      return;
    }

    target.scrollIntoView({ block: "center", inline: "center", behavior: "smooth" });
    flashTarget(target, "#15803d");
    target.focus?.();
    advanceRuntime(runtime, step.delayMs);
    target.click();
    showToast(`Clicked: ${step.label}`, "success");
  }

  function handleProfileStep(profile, runtime, step) {
    switch (step.type) {
      case "click":
        handleProfileClick(profile, runtime, step);
        return;
      case "back":
        advanceRuntime(runtime);
        showToast(`Back ${step.count} page(s): ${step.label}`, "info");
        window.setTimeout(() => {
          window.history.go(-step.count);
        }, 60);
        return;
      case "wait":
        advanceRuntime(runtime, step.delayMs);
        return;
      case "waitfortext": {
        const textReady = step.text ? pageHasText(step.text) : true;
        const textGoneReady = step.textGone ? !pageHasText(step.textGone) : true;

        if (textReady && textGoneReady) {
          advanceRuntime(runtime, step.delayMs);
          return;
        }

        if (Date.now() - runtime.stepStartedAt >= step.timeoutMs) {
          pauseRuntime(`Stopped at ${profile.label}: wait timed out for ${step.label}.`);
          return;
        }

        scheduleProfileContinue(PROFILE_RETRY_DELAY_MS);
        return;
      }
      case "dialogpolicy":
        writeStorage(
          DIALOG_POLICY_KEY,
          normalizeDialogPolicy({
            confirm: step.confirmMode,
            alert: step.alertMode,
          })
        );
        advanceRuntime(runtime, step.delayMs);
        return;
      default:
        pauseRuntime(`Unsupported step type at ${step.label}.`);
    }
  }

  function continueProfile() {
    if (continueProfile.running) {
      return;
    }

    const runtime = getRuntime();
    if (!runtime || runtime.paused) {
      return;
    }

    const profile = getProfileBySlot(runtime.slot);
    if (!profile) {
      clearRuntime();
      showToast("Saved active profile no longer exists.", "error");
      return;
    }

    const step = profile.steps[runtime.stepIndex];
    if (!step) {
      clearRuntime();
      writeStorage(DIALOG_POLICY_KEY, { confirm: "prompt", alert: "prompt" });
      showToast(`${profile.label} complete.`, "success");
      return;
    }

    continueProfile.running = true;
    try {
      handleProfileStep(profile, runtime, step);
    } finally {
      continueProfile.running = false;
    }
  }
  continueProfile.running = false;
  continueProfile.timerId = 0;

  function getNextStep() {
    const plan = getPlan();
    const index = getIndex();
    return { plan, index, step: plan[index] || null };
  }

  function previewNext() {
    const { plan, index, step } = getNextStep();

    if (!plan.length) {
      showToast("No plan saved yet.", "error");
      return null;
    }

    if (!step) {
      showToast("Plan complete. Press Alt+Shift+R to reset.", "success");
      return null;
    }

    const target = findTarget(step);

    if (!target) {
      showToast(`No match for ${step.label}.`, "error");
      return null;
    }

    target.scrollIntoView({ block: "center", inline: "center", behavior: "smooth" });
    flashTarget(target, "#2563eb");
    showToast(`Preview: ${step.label}`, "info");
    return target;
  }

  function runNext() {
    const { plan, index, step } = getNextStep();

    if (!plan.length) {
      showToast("No plan saved yet.", "error");
      return null;
    }

    if (!step) {
      showToast("Plan complete. Press Alt+Shift+R to reset.", "success");
      return null;
    }

    const target = findTarget(step);

    if (!target) {
      showToast(`No match for ${step.label}.`, "error");
      return null;
    }

    if (isRisky(target, step)) {
      target.scrollIntoView({ block: "center", inline: "center", behavior: "smooth" });
      flashTarget(target, "#b91c1c");
      showToast(`Blocked risky click for ${step.label}.`, "error");
      return null;
    }

    target.scrollIntoView({ block: "center", inline: "center", behavior: "smooth" });
    flashTarget(target, "#15803d");
    target.focus?.();
    target.click();
    setIndex(index + 1);
    showToast(`Clicked: ${step.label}`, "success");
    return target;
  }

  function isTypingTarget(element) {
    if (!(element instanceof Element)) {
      return false;
    }

    const tagName = element.tagName.toLowerCase();
    return (
      element.isContentEditable ||
      tagName === "input" ||
      tagName === "textarea" ||
      tagName === "select"
    );
  }

  function getProfileSlotFromEvent(event) {
    if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) {
      return 0;
    }

    const match = /^Digit([1-9])$/.exec(event.code) || /^Numpad([1-9])$/.exec(event.code);
    return match ? Number(match[1]) : 0;
  }

  function hotkeyMatches(event, hotkey) {
    return (
      event.code === hotkey.code &&
      event.altKey === Boolean(hotkey.altKey) &&
      event.shiftKey === Boolean(hotkey.shiftKey) &&
      event.ctrlKey === Boolean(hotkey.ctrlKey) &&
      event.metaKey === Boolean(hotkey.metaKey)
    );
  }

  document.addEventListener("keydown", (event) => {
    if (event.repeat || isTypingTarget(event.target)) {
      return;
    }

    const profileSlot = getProfileSlotFromEvent(event);
    if (profileSlot) {
      event.preventDefault();
      startProfile(profileSlot);
      return;
    }

    if (hotkeyMatches(event, HOTKEY)) {
      event.preventDefault();
      runNext();
      return;
    }

    if (hotkeyMatches(event, PREVIEW_HOTKEY)) {
      event.preventDefault();
      previewNext();
      return;
    }

    if (hotkeyMatches(event, RESET_HOTKEY)) {
      event.preventDefault();
      reset();
      return;
    }

    if (hotkeyMatches(event, STOP_HOTKEY)) {
      event.preventDefault();
      stopProfile();
    }
  });

  window.HotkeyClickRunner = {
    clearProfiles,
    clearPlan,
    clearRuntime,
    getDialogPolicy,
    getProfiles,
    getPlan,
    getRuntime,
    previewNext,
    reset,
    resumeProfile,
    runNext,
    setDialogPolicy,
    setExpandedPlan,
    setPlan,
    setProfiles,
    startProfile,
    status,
    stopProfile,
    examplePlan: [
      {
        label: "Category 1 - Open returns",
        sectionTitle: "Category Name Here",
        accountNumber: "0000-0000",
        actionText: "View Returns and Periods",
      },
      {
        label: "Step on next page",
        actionText: "Continue",
        urlIncludes: ["/returns"],
      },
    ],
    exampleProfiles: [
      {
        slot: 1,
        label: "Category 1",
        steps: [
          {
            label: "Open first category",
            selector: "#caption2_Dl-n1-1",
          },
          {
            label: "Open amendable return",
            actionText: "View or Amend Return",
          },
          {
            label: "Click Amend",
            actionText: "Amend",
          },
          {
            label: "Next",
            actionText: "Next",
          },
          {
            label: "Allow browser confirm",
            type: "dialogPolicy",
            confirmMode: "accept",
          },
          {
            label: "Submit",
            actionText: "Submit",
            allowRisky: true,
          },
          {
            label: "Press OK",
            actionText: "OK",
            allowRisky: true,
          },
          {
            label: "Go back two pages",
            type: "back",
            count: 2,
          },
        ],
      },
    ],
  };

  window.setTimeout(() => {
    continueProfile();
  }, 400);

  console.info(
    "[HotkeyClickRunner] Ready. Hotkeys: 1-9 start profiles, Alt+Shift+K run next, Alt+Shift+J preview, Alt+Shift+R reset, Alt+Shift+X stop."
  );
})();
