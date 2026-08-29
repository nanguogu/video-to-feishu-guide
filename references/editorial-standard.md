# Editorial standard

## Design the guide around reader decisions

The recording is evidence of the workflow, not the document outline. A good guide preserves the operations required for success while removing timeline noise such as cursor travel, loading pauses, repeated confirmations, and familiar micro-interactions.

Use this decision matrix when deciding whether to merge or expand actions:

| Situation | Treatment |
|---|---|
| Familiar routine interaction, such as entering an account, requesting a code, and signing in | Merge into one goal-level step |
| The next step or screenshot visibly proves the previous action succeeded | Omit a separate result paragraph |
| Wrong choice could join the wrong organization, use the wrong account, publish data, or trigger an irreversible action | Expand and add a warning |
| Completion is silent or readers commonly confuse an intermediate state with success | Keep one explicit completion check |
| CAPTCHA, retry, timeout, or rare failure | Mention inline only if unavoidable; otherwise move to troubleshooting |
| Operation is not demonstrated in the recording | Mark it optional or out of scope; do not invent instructions |

## Recommended information architecture

Use the smallest structure that makes the task safe and understandable:

1. Outcome and approximate time.
2. Audience and preparation.
3. Main path grouped by user goals.
4. One critical completion checklist.
5. Troubleshooting based on observed or highly probable failures.
6. Scope and freshness note when product screens may change.

Do not force a fixed number of steps. Most short software workflows become clearer when routine authentication and verification are compressed, but complex or high-risk workflows may require more detail.

## Step writing

Each main step normally contains:

- A goal-oriented heading.
- One direct action paragraph.
- One screenshot placed immediately after that paragraph.
- A warning only when skipping it could cause a real mistake.

Avoid the mechanical pattern “what to do / what you should see / screenshot / tip” on every step. Use an explicit success statement only at a meaningful boundary.

## Screenshots and annotations

- Select state changes and decision points, not evenly spaced timestamps.
- Prefer one screenshot that shows the full familiar interaction over several screenshots of each field.
- Crop enough surrounding context for orientation.
- Use a red rectangle and a numbered marker for click targets. Number multiple targets only when the order matters.
- Keep captions short and outcome-oriented. Do not repeat the full instruction in the caption.
- After removing screenshots, renumber the remaining figures continuously.

## UI wording convention

- Clickable button or menu label: `【<b>登录</b>】` in Feishu XML, or `**【登录】**` in Markdown.
- Non-clickable status or message: “加入成功”.
- Field names may use plain text unless they are easily confused with surrounding copy.

This distinction lets a reader scan for actions without mistaking status text for something clickable.

## Privacy and fidelity

Redact sensitive areas before publishing. Prefer opaque masking for OTPs, tokens, invite URLs, and secrets; blur may still reveal short or high-contrast strings. Inspect every final screenshot at full size.

Never infer missing steps from product familiarity alone. If a step is necessary but not visible, label it as an assumption and request confirmation, or keep it outside the demonstrated procedure.
