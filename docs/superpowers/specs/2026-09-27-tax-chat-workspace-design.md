# Tax research chat workspace

Approved in conversation on 2026-09-27: chat-first, a case sidebar, inline fact confirmation, guided clarification, and a collapsible source panel. Add restrained tax/finance icons. The user explicitly authorized implementation; do not merge `demo/hk-web`.

## Scope and architecture

Build an original Chinese-language React/TypeScript front end under `apps/web`, served by Vite independently of the existing Python application. The main branch exposes only `/health`; this delivery is an explicitly labelled, deterministic interaction preview, not live AI or a tax assessment. No credentials, external model calls, uploads, or customer data storage. Conversations live in memory and reset on reload.

The initial page is a quiet, light research workspace: navy navigation, off-white canvas, teal accents, an illustrated financial motif made from icons, three synthetic starting prompts, and a large composer. A chat contains user messages, a fact card, receipt-location clarification, and a research checklist with official-source links. Unknown values stay unknown. Editing confirmed facts invalidates the previous checklist. Unsupported topics receive a scope message, not fabricated advice.

Components: app owns cases and active panel; sidebar owns case search; conversation renders messages and facts; composer owns draft and IME-safe submission; details panel handles fact editing, sources and research boundaries. A pure demo state module separates fixture behaviour from a future API adapter. Source metadata uses the existing repository manifest and is labelled as an index, not retrieved statutory text.

## Interaction and accessibility

- Create, search and switch cases without leaking one case's facts into another.
- Submit with Enter; Shift+Enter adds a line; Chinese IME confirmation must not submit.
- Confirm or edit candidate facts, then choose a receipt scenario including unknown.
- Citations open their matching source; original official links open separately.
- Desktop case panel pushes the conversation; mobile uses a keyboard-accessible modal with focus restoration, Escape and backdrop dismissal.
- Use labelled controls, visible focus, adequate contrast and reduced-motion support.
- Icons: Lucide Scale, Landmark, BookOpen, Coins, ReceiptText, ShieldCheck and CircleHelp with descriptive labels. No external template code or assets copied.

## Evidence and implementation sequence

GitHub research: `vercel/chatbot` (Apache-2.0, conversation architecture only), `lucide-icons/lucide` (ISC/MIT icon notices retained), `vitejs/vite` (MIT, current releases/security policy/issues checked). Vite 8.3.1 requires Node 20.19+ or 22.12+; local Node 22.17 satisfies this. Do not adopt the full Next.js backend because Python already owns analysis. Lock dependencies and run audit.

1. Scaffold React/TypeScript/Vite and original design tokens.
2. Implement state, chat, fact editing, citations, case navigation and responsive layout.
3. Add focused browser tests for the full case flow, isolation, stale-result invalidation, mobile and keyboard behaviour.
4. Run TypeScript/build, dependency audit and browser verification; update run instructions and CI.

Acceptance: the app launches without backend services, all visible actions work, the preview status is persistent, no generated legal conclusions or fake quotations appear, and desktop/mobile checks pass. Database/model integration, PDF ingestion, scenario comparison and exports are intentionally future work.
