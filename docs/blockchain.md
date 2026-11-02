# Blockchain audit design

`JanSetuAudit.sol` accepts complaint reference, event type and event-data hashes from authorized signers. It contains no citizen PII or descriptions. The frontend/API reports `PENDING` for database events unless a chain transaction is explicitly confirmed. The current API adapter records hashes in the database but does not submit a transaction: configure a signer, deploy the contract, and implement transaction receipt verification before enabling confirmed state.
