import { createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";

class DeliverableVerifier {
  constructor(contractAddress, account = null, studioUrl = null) {
    this.contractAddress = contractAddress;
    this.studioUrl = studioUrl;
    this.client = createClient({
      chain: studionet,
      ...(account ? { account } : {}),
      ...(studioUrl ? { endpoint: studioUrl } : {}),
    });
  }

  updateAccount(account) {
    this.client = createClient({
      chain: studionet,
      account,
      ...(this.studioUrl ? { endpoint: this.studioUrl } : {}),
    });
  }

  async getSubmission(submissionId) {
    return this.client.readContract({
      address: this.contractAddress,
      functionName: "get_submission",
      args: [submissionId],
    });
  }

  async createSubmission(submissionId, title, requirements, deliverableUrl) {
    const hash = await this.client.writeContract({
      address: this.contractAddress,
      functionName: "create_submission",
      args: [submissionId, title, requirements, deliverableUrl],
    });
    return this.client.waitForTransactionReceipt({
      hash,
      status: "FINALIZED",
      interval: 5000,
      retries: 30,
    });
  }

  async evaluateSubmission(submissionId) {
    const hash = await this.client.writeContract({
      address: this.contractAddress,
      functionName: "evaluate_submission",
      args: [submissionId],
    });
    return this.client.waitForTransactionReceipt({
      hash,
      status: "FINALIZED",
      interval: 10000,
      retries: 30,
    });
  }
}

export default DeliverableVerifier;
