# Deliverable Verifier

Deliverable Verifier is a GenLayer Intelligent Contract that turns a plain-English brief and a public deliverable URL into an auditable, consensus-backed acceptance decision.

It is designed as the first contribution for the GenLayer Builder program: small enough to submit as an Intelligent Contract, but useful enough to grow into agent bounties, escrow, and reputation workflows.

## Why GenLayer

The contract is authoritative over the part that needs GenLayer: validators independently fetch the public deliverable, interpret the requirements, and agree on the final `passed` decision and a score tolerance. The UI owns convenience flows and presentation; the external page remains the source of evidence.

The contract uses a custom equivalence rule rather than strict equality:

- `passed` must match exactly.
- `score` must be within 15 points.
- Explanations and evidence are stored from the accepted result for auditability.

## Contract flow

1. `create_submission` stores a title, requirements, and an HTTP(S) deliverable URL.
2. `evaluate_submission` fetches the URL in a nondeterministic block and asks the LLM for structured JSON.
3. GenLayer validators independently repeat the evaluation and check the equivalence rule.
4. The contract stores `approved` or `rejected`, the score, summary, and evidence.

## Local setup

Install the Python dependencies:

```powershell
python -m pip install -r requirements.txt
```

Lint the contract before testing:

```powershell
genvm-lint check contracts/deliverable_verifier.py
```

Run direct tests:

```powershell
pytest tests/direct -v
```

The direct tests mock web content and LLM output. They verify deterministic state transitions, input validation, duplicate protection, and both approval and rejection paths. Direct mode does not exercise live validator agreement; run an integration test against GenLayer Studio before deployment.

## Deploy

Configure the CLI for the target network, then deploy from the project root:

```powershell
genlayer network set studionet
genlayer deploy --contract contracts/deliverable_verifier.py
```

For a local Studio environment, use the network configuration appropriate to that Studio. Inspect the deployment receipt and confirm execution succeeded before using the contract address.

### Current StudioNet deployment

- Contract: `0x5FeB7C2bf7c9AC656aB5205ad1eB6420899cfCaC`
- Deployment transaction: `0xf5492ee0ab9221b785d2651e7634b83979e3eda9afef3d0fcf2d18b6e740218b`
- Receipt: accepted with majority agreement on StudioNet

## Demo UI

After deployment, copy `app/.env.example` to `app/.env` and set:

```text
VITE_CONTRACT_ADDRESS=0x...
VITE_STUDIO_URL=https://studio.genlayer.com/api
```

The checked-in local workspace already has `app/.env` configured for the current StudioNet deployment.

Then run:

```powershell
cd app
npm install
npm run dev
```

## Contribution packaging

See [`SUBMISSION.md`](SUBMISSION.md) for the Builder submission checklist and the evidence we should attach after deployment.
