# Userscripts

`hotkey-click-runner.user.js` is a generic browser helper for repetitive click paths on third-party sites.

Use it when:

- the site makes you repeat the same navigation clicks over and over
- the target page is not part of this repo
- you want one hotkey instead of hunting buttons with the mouse

## Install

1. Install Tampermonkey or Violentmonkey in your browser.
2. Create a new userscript.
3. Paste in the contents of `hotkey-click-runner.user.js`.
4. Save it.
5. Open the target site.

## Hotkeys

- `Alt+Shift+K`: click the next saved step
- `Alt+Shift+J`: preview the next match without clicking it
- `Alt+Shift+R`: reset the saved step index back to the first step

## Console API

Open browser devtools and use `window.HotkeyClickRunner`.

Save a direct plan:

```js
HotkeyClickRunner.setPlan([
  {
    label: "Category 1",
    sectionTitle: "Category Name Here",
    accountNumber: "0000-0000",
    actionText: "View Returns and Periods"
  },
  {
    label: "Next page action",
    actionText: "Continue",
    urlIncludes: ["/returns"]
  }
]);
```

Build a repeated plan from categories plus shared actions:

```js
HotkeyClickRunner.setExpandedPlan(
  [
    { sectionTitle: "Category A", accountNumber: "0000-0000" },
    { sectionTitle: "Category B", accountNumber: "1111-1111" }
  ],
  [
    { actionText: "View Returns and Periods" },
    { actionText: "Continue", urlIncludes: ["/returns"] }
  ]
);
```

Check progress:

```js
HotkeyClickRunner.status();
```

Clear saved data:

```js
HotkeyClickRunner.clearPlan();
```

## Matching Order

Each step can target by:

- `selector`: direct CSS selector
- `xpath`: direct XPath expression
- `actionText`: visible link or button text

If you use `actionText`, the runner scores nearby text too:

- `sectionTitle`
- `accountNumber`
- `contextText`
- `urlIncludes`

That makes it more reliable than clicking the first matching button on the page.

## Guard Rails

By default the runner blocks clicks whose visible text looks like a final action:

- `Submit`
- `Confirm`
- `Authorize`
- `Sign`
- `Finalize`

If you really need a final-action click, add `allowRisky: true` on that one step.

## Notes

- Keep private business data out of tracked files. Save your real plan in the browser console or a local untracked note.
- Once you send the page HTML, this can be tightened with exact selectors instead of text matching.
