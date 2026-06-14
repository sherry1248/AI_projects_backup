# Demo UX Flow Refinement Log

## Scope

Refined the Gradio demo UX flow without adding Agent features.

## Changes

- Kept the default screen centered on the 상담 채팅 experience.
- Fixed the chat window height so previous messages can be reviewed by scrolling.
- Preserved assistant-role first greeting as an initial chat bubble.
- Made status check optional through the `상태 체크하기` next-step button and collapsed section.
- Kept emotion scores inside the 감정일기 flow.
- Added nickname UX behavior:
  - anonymous mode on: nickname input disabled
  - anonymous mode off: nickname input enabled
- Reframed post-chat actions as next steps:
  - 상태 체크하기
  - 감정일기 쓰기
  - 마음정리 보고서 보기
  - 전문가 상담 연결
- Kept Agent Pipeline Details as a collapsed debug accordion.

## Safety and Privacy

- Safety/crisis flow was not changed.
- Internal guidance remains hidden.
- Raw user input, raw dataset text, and raw memory transcript remain excluded from the user-facing UI and debug panel.

