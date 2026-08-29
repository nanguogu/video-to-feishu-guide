# Feishu publishing workflow

Use this reference only when the requested deliverable is a Feishu online document.

## Prerequisites

1. Use the `lark-doc` skill when it is available and read its required authentication, XML, style, fetch, update, and media instructions before writing.
2. Verify the Feishu user identity. Create the document with `--as user` so the requester owns and can access it.
3. Keep draft XML and all media under the current working directory. `lark-cli` file arguments must use relative paths.

## Publish sequence

1. Create the complete text structure first. Use one `<title>` and do not repeat the same title as the first heading.
2. Fetch the document with block IDs.
3. Insert only redacted screenshots with `docs +media-insert`.
4. Move each returned image block immediately after its corresponding action paragraph using `block_move_after`.
5. When a step is removed, delete its obsolete image block and renumber remaining figure captions.
6. Use precise block edits instead of overwriting the whole document after images have been inserted.

## XML conventions

- Button: `点击【<b>立即加入</b>】`
- Status: `页面显示“加入成功”`
- Critical warning: reserve a callout for a mistake with real consequences, such as joining the wrong organization.
- Completion: use a short checkbox list when several conditions jointly prove success.

Image captions do not support reliable partial bolding. If a caption would repeat a button label without the required formatting, rewrite it as a short outcome description instead.

## Final verification

Fetch the final document XML and verify:

- One title and no duplicate first heading.
- Continuous step and figure numbering.
- Every screenshot follows the action it illustrates.
- No placeholder text.
- No routine “完成后应该看到” repetition.
- Clickable labels use bold `【按钮】`; quoted text is reserved for statuses.
- Raw account data, invite links, codes, tokens, and unrelated personal information are absent.
- The final success state remains explicit.

If authorization fails, stop the publishing step and use the normal Feishu user authorization flow. Do not silently create a bot-owned document that the requester cannot access.
