# Deliverable Verifier demo

This Vue app is a thin client for the `DeliverableVerifier` contract. It uses `genlayer-js` 1.1.8 with the StudioNet chain, creates a local GenLayer account, registers a brief, reads the on-chain result, and submits an evaluation transaction.

Set `VITE_CONTRACT_ADDRESS` in `.env` to a deployed contract before using the transaction buttons. `VITE_STUDIO_URL` can point to local Studio or the hosted Studio API endpoint.
