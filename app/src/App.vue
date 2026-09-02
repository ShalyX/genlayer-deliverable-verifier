<template>
  <div class="shell">
    <header class="hero">
      <div>
        <p class="eyebrow">GENLAYER INTELLIGENT CONTRACT</p>
        <h1>Deliverable Verifier</h1>
        <p class="lede">
          Turn plain-English acceptance criteria into an auditable,
          consensus-backed decision.
        </p>
      </div>
      <div class="account-card">
        <span v-if="userAddress" class="account-address">{{ shorten(userAddress) }}</span>
        <button v-if="!userAddress" class="button secondary" @click="createUserAccount">
          Create local account
        </button>
        <button v-else class="button quiet" @click="disconnectUserAccount">
          Disconnect
        </button>
      </div>
    </header>

    <main class="content">
      <section class="panel form-panel">
        <div class="section-heading">
          <div>
            <p class="eyebrow">NEW SUBMISSION</p>
            <h2>Define the brief</h2>
          </div>
          <span class="status-pill pending">PENDING → VERIFIED</span>
        </div>

        <form @submit.prevent="submitBrief">
          <label>
            Submission ID
            <input v-model.trim="form.id" required placeholder="release-v1" />
          </label>
          <label>
            Title
            <input v-model.trim="form.title" required placeholder="Release checklist" />
          </label>
          <label>
            Acceptance requirements
            <textarea
              v-model.trim="form.requirements"
              required
              rows="5"
              placeholder="The deliverable must contain a rollback plan..."
            />
          </label>
          <label>
            Public deliverable URL
            <input
              v-model.trim="form.url"
              required
              type="url"
              placeholder="https://example.com/deliverable"
            />
          </label>
          <button class="button primary" :disabled="busy || !contractReady">
            {{ busy ? "Submitting…" : "Create submission" }}
          </button>
        </form>
      </section>

      <section class="panel result-panel">
        <div class="section-heading">
          <div>
            <p class="eyebrow">ON-CHAIN RESULT</p>
            <h2>Review a submission</h2>
          </div>
          <button class="button quiet" :disabled="busy || !form.id || !contractReady" @click="loadSubmission">
            Refresh
          </button>
        </div>

        <div v-if="!contractReady" class="notice">
          Add <code>VITE_CONTRACT_ADDRESS</code> to <code>app/.env</code> after deployment.
        </div>
        <div v-else-if="!submission" class="empty-state">
          Create a submission, then evaluate it once the deliverable is ready.
        </div>
        <div v-else class="result-card">
          <div class="result-topline">
            <span class="status-pill" :class="submission.status">{{ submission.status }}</span>
            <strong>{{ submission.score }}/100</strong>
          </div>
          <h3>{{ submission.title }}</h3>
          <p>{{ submission.summary || "Awaiting consensus evaluation." }}</p>
          <dl v-if="submission.evidence">
            <dt>Evidence</dt>
            <dd>{{ submission.evidence }}</dd>
          </dl>
          <button
            v-if="submission.status === 'pending'"
            class="button primary"
            :disabled="busy || !userAddress"
            @click="evaluateBrief"
          >
            {{ busy ? "Evaluating…" : "Evaluate with GenLayer" }}
          </button>
          <p v-if="!userAddress" class="helper">Create a local account to send transactions.</p>
        </div>
      </section>
    </main>

    <p v-if="message" class="message" :class="{ error: error }">{{ message }}</p>
    <footer>Deliverable Verifier · Built for the GenLayer Builder contribution program</footer>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from "vue";
import { account, createAccount, removeAccount } from "./services/genlayer";
import DeliverableVerifier from "./logic/DeliverableVerifier";

const contractAddress = import.meta.env.VITE_CONTRACT_ADDRESS;
const studioUrl = import.meta.env.VITE_STUDIO_URL;
const userAccount = ref(account);
const verifier = new DeliverableVerifier(contractAddress, account, studioUrl);
const submission = ref(null);
const busy = ref(false);
const message = ref("");
const error = ref(false);
const form = reactive({ id: "release-v1", title: "Release checklist", requirements: "", url: "" });

const userAddress = computed(() => userAccount.value?.address || "");
const contractReady = computed(() => Boolean(contractAddress));

const shorten = (address) => `${address.slice(0, 6)}…${address.slice(-4)}`;

const createUserAccount = () => {
  userAccount.value = createAccount();
  verifier.updateAccount(userAccount.value);
  message.value = "Local account ready.";
  error.value = false;
};

const disconnectUserAccount = () => {
  userAccount.value = null;
  removeAccount();
  verifier.updateAccount(null);
  message.value = "Account disconnected.";
};

const loadSubmission = async () => {
  if (!form.id || !contractReady.value) return;
  busy.value = true;
  message.value = "";
  error.value = false;
  try {
    submission.value = await verifier.getSubmission(form.id);
  } catch (err) {
    submission.value = null;
    message.value = err?.message || "Submission not found yet.";
    error.value = true;
  } finally {
    busy.value = false;
  }
};

const submitBrief = async () => {
  if (!userAddress.value || !contractReady.value) return;
  busy.value = true;
  message.value = "";
  error.value = false;
  try {
    await verifier.createSubmission(form.id, form.title, form.requirements, form.url);
    await loadSubmission();
    message.value = "Submission created. Run the consensus evaluation when ready.";
  } catch (err) {
    message.value = err?.message || "Could not create submission.";
    error.value = true;
  } finally {
    busy.value = false;
  }
};

const evaluateBrief = async () => {
  if (!submission.value || !userAddress.value) return;
  busy.value = true;
  message.value = "Validators are evaluating the public deliverable…";
  error.value = false;
  try {
    await verifier.evaluateSubmission(submission.value.id);
    await loadSubmission();
    message.value = "Evaluation finalized on GenLayer.";
  } catch (err) {
    message.value = err?.message || "Could not evaluate submission.";
    error.value = true;
  } finally {
    busy.value = false;
  }
};
</script>
