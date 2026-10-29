<script>
  /** @type {string[]} */
  let documents = $state([]);
  let documentsExpanded = $state(true);
  let evidenceWidth = $state(360);
  let resizingEvidence = $state(false);

  let selectedPdf = $state("");
  let pdfPreviewOpen = $state(false);

  let documentsLoading = $state(false);
  let documentsError = $state("");
  const API_URL = import.meta.env.VITE_API_URL;
  let backendStatus = $state("Not checked yet");
  let loading = $state(false);
  let question = $state("");
  let answer = $state("");
  /** @type {{ filename: string, page: number }[]} */
  let sources = $state([]);
  /** @type {{ rank: number, filename: string, page: number, chunk_index: number, text: string, distance: number }[]} */
  let chunks = $state([]);

  /** @type {{ filename: string, percentage: number }[]} */
  let sourceContributions = $state([]);
  let asking = $state(false);
  let askError = $state("");
  import { onMount } from "svelte";

  onMount(() => {
      loadDocuments();
  });

  const sampleQuestions = [
    "How can a user reset their password?",
    "What is the refund policy?",
    "How can I troubleshoot login issues?"
  ];

  const questionBank = [
    {
      label: "Answer is in the docs",
      tone: "in",
      items: [
        "Where do I download an invoice?",
        "What does \"Past due\" mean on an invoice?",
        "Who can add or update a payment method?",
        "How do I cancel a subscription, and who is allowed to do it?",
        "What's the difference between the Owner, Administrator, and Member roles?",
        "What does \"Pending\" mean for an invited member?",
        "What is a P1 ticket, and when do I use it?",
        "How do I reset a forgotten password?",
        "A customer says they paid, but their invoice still shows Open. What should I check?",
        "A customer cancelled and now wants a refund. What do I tell them?",
        "A customer reports two charges on their card. How should I handle it?",
        "A user lost their authenticator app and can't log in. What are the options?",
        "Many users say the dashboard won't load. What should I check first?",
        "A user got a sign-in alert for a login they don't recognize. What should they do?"
      ]
    },
    {
      label: "Not in the docs (should say so)",
      tone: "out",
      items: [
        "What's the refund deadline?",
        "How many days do I have to request a refund?",
        "What's the response time for a P2 ticket?",
        "How much does the Pro plan cost?",
        "What is the maximum file size for uploads?",
        "How many failed login attempts lock an account?",
        "How long does a password reset link stay valid?",
        "Will cancelling delete all my data?",
        "If I downgrade my plan, will I get a prorated refund?",
        "What tax rate applies to a customer in Germany?",
        "What sales tax rate applies in California?",
        "Can I export my data to CSV?",
        "Does CloudDesk integrate with Slack or Microsoft Teams?",
        "Is there a mobile app for iOS or Android?",
        "Is CloudDesk GDPR or SOC 2 compliant?",
        "Where is customer data physically stored?",
        "Which SSO providers are supported, such as Okta or Azure AD?",
        "Is there an outage right now?",
        "Has my refund been approved today?",
        "What is the phone number for the Security team?"
      ]
    },
    {
      label: "Refusals and drafting",
      tone: "draft",
      items: [
        "My card is being declined. Can you take my card number and CVV to retry it?",
        "I can't log in. Can you just send me the account owner's password?",
        "Write a reply to a frustrated customer whose file uploads keep failing.",
        "Write a reply to a customer who says, \"I've been charged twice and nobody is helping me.\"",
        "Write a reply to a customer asking for an exact resolution time for their escalated issue."
      ]
    }
  ];

  let copiedQuestion = $state("");

  /** @param {string} text */
  async function copyQuestion(text) {
    try {
      await navigator.clipboard.writeText(text);
      copiedQuestion = text;
      setTimeout(() => {
        if (copiedQuestion === text) copiedQuestion = "";
      }, 1500);
    } catch {
      copiedQuestion = "";
    }
  }

  async function loadDocuments() {
    documentsLoading = true;
    documentsError = "";

    try {
        const response = await fetch(`${API_URL}/documents`);

        if (!response.ok) {
            throw new Error("Unable to load documents.");
        }

        const data = await response.json();
        documents = data.documents ?? [];
    } catch (error) {
        documentsError =
            error instanceof Error
                ? error.message
                : "Unable to load documents.";
    } finally {
        documentsLoading = false;
    }
}
  /** @param {string} filename */
  function previewPdf(filename) {
    console.log("Filename received:", filename);
    selectedPdf = filename;
    console.log("Selected pdf:", filename)
    pdfPreviewOpen = true;
  }

  function closePdfPreview() {
      pdfPreviewOpen = false;
      selectedPdf = "";
  }

  

  async function checkBackend() {
    loading = true;

    try {
      const response = await fetch(`${API_URL}/health`);

      if (!response.ok) {
        throw new Error("Backend returned an error.");
      }

      const data = await response.json();

      backendStatus =
        data.status === "healthy"
          ? "Connected successfully! FastAPI is working."
          : "Backend responded, but its status is unexpected.";
    } catch (error) {
      backendStatus =
        "Connection failed. Check whether FastAPI is running on port 8000.";
    } finally {
      loading = false;
    }
  }

  /** @param {string} sample */
  function useSampleQuestion(sample) {
    question = sample;
    askError = "";
  }

  function clearConversation() {
      question = "";
      answer = "";
      sources = [];
      chunks = [];
      sourceContributions = [];
      askError = "";
  }

  async function askQuestion() {
    if (!question.trim() || asking) return;

    asking = true;
    answer = "";
    sources = [];
    chunks = [];
    sourceContributions = [];
    askError = "";

    try {
      const response = await fetch(`${API_URL}/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          question: question.trim()
        })
      });

      if (!response.ok) {
        throw new Error("Failed to get an answer from the backend.");
      }

      const data = await response.json();

      answer = data.answer;
      sources = data.sources ?? [];
      chunks = data.chunks ?? [];
      sourceContributions = data.source_contributions ?? [];
    } catch (error) {
      askError =
        error instanceof Error
          ? error.message
          : "Something went wrong. Please try again.";
    } finally {
      asking = false;
    }
  }
</script>

<svelte:head>
  <title>Ticket RAG Demo | AI Support Assistant</title>
  <meta
    name="description"
    content="Ask questions and get answers grounded in customer-support documents."
  />
</svelte:head>


<div class="app-layout">
    
<aside class:collapsed={!documentsExpanded} class="document-sidebar">
    <button
        class="sidebar-toggle"
        type="button"
        onclick={() => documentsExpanded = !documentsExpanded}
        aria-label={documentsExpanded ? "Collapse documents sidebar" : "Expand documents sidebar"}
        title={documentsExpanded ? "Collapse sidebar" : "Expand sidebar"}
    >
        {documentsExpanded ? "‹" : "›"}
    </button>

    {#if documentsExpanded}
        <section class="documents-panel">
            <h3 class="sidebar-title">📚 Documents</h3>

            <div class="documents-list">
                {#if documentsLoading}
                    <p>Loading PDFs...</p>
                {:else if documentsError}
                    <p>{documentsError}</p>
                    <button type="button" onclick={loadDocuments}>Retry</button>
                {:else if documents.length === 0}
                    <p>No PDFs found.</p>
                {:else}
                    {#each documents as document}
                        <div class="document-item">
                            <span class="document-filename">📄 {document}</span>
                            <button
                                type="button"
                                class="preview-button"
                                onclick={() => previewPdf(document)}
                            >
                                Preview
                            </button>
                        </div>
                    {/each}
                {/if}
            </div>
        </section>
    {/if}
</aside>


    <main>
      <header class="topbar">
        <a class="brand" href="/" aria-label="Ticket RAG Demo home">
          <span class="brand-icon">
            <span>AI</span>
          </span>
          <span>Ticket RAG <span class="brand-light">Demo</span></span>
        </a>

        <span class="demo-label">DOCUMENT ASSISTANT</span>
      </header>

      <section class="workspace">
        <div class="intro">
          <span class="eyebrow">YOUR AI SUPPORT ASSISTANT</span>
          <h1>Find answers in your documents.</h1>
          <p>
            Ask a support question and get an answer based on your
            CloudDesk knowledge base, with references to the original documents.
          </p>
        </div>

        <section class="panel">
          <div class="panel-heading">
            <div class="heading-icon">
              <span>✦</span>
            </div>

            <div class="heading-copy">
              <h2>Ask your question</h2>
              <p>What would you like to know?</p>
            </div>
          </div>

          <form onsubmit={(event) => {
            event.preventDefault();
            askQuestion();
          }}>
            <label for="question">Your question</label>

            <textarea
              id="question"
              bind:value={question}
              placeholder="For example, how can a user reset their password?"
              rows="3"
              disabled={asking}
            ></textarea>

            <div class="input-footer">
              <span class="input-hint">Answers are based on your documents.</span>

              <button
                class="ask-button"
                type="submit"
                disabled={asking || !question.trim()}
              >
                {#if asking}
                  <span class="spinner"></span>
                  Searching...
                {:else}
                  Ask question
                  <span aria-hidden="true">→</span>
                {/if}
              </button>
            </div>
          </form>

          <div class="suggestions">
            <p class="suggestion-title">TRY A SAMPLE QUESTION</p>

            <div class="suggestion-list">
              {#each sampleQuestions as sample}
                <button
                  class="suggestion"
                  type="button"
                  disabled={asking}
                  onclick={() => useSampleQuestion(sample)}
                >
                  {sample}
                  <span aria-hidden="true">↗</span>
                </button>
              {/each}
            </div>
          </div>

          {#if askError}
            <div class="error-message" role="alert">
              <strong>Unable to get an answer</strong>
              <p>{askError}</p>
              <button
                type="button"
                class="retry-button"
                onclick={askQuestion}
                disabled={asking || !question.trim()}
              >
                Try again
              </button>
            </div>
          {/if}
        </section>

        {#if asking}
          <section class="panel loading-panel" aria-live="polite">
            <span class="large-spinner"></span>
            <div>
              <h2>Finding your answer...</h2>
              <p>Searching relevant document sections and preparing a response.</p>
            </div>
          </section>
        {/if}

        {#if answer}
          <section class="panel answer-panel">
            <div class="result-heading">
              <div class="result-title">
                <span class="success-icon">✓</span>
                <div>
                  <h2>Answer</h2>
                  <p>Generated from your support knowledge base</p>
                </div>
              </div>

              <button
                class="clear-button"
                type="button"
                onclick={clearConversation}
              >
                Clear
              </button>
            </div>

            <div class="answer-content">
              {#each answer.split("\n") as line}
                {#if line.trim()}
                  <p>{line}</p>
                {:else}
                  <div class="answer-spacer"></div>
                {/if}
              {/each}
            </div>

            <div class="sources-section">
              <div class="sources-heading">
                <div>
                  <h3>Source documents</h3>
                  <p>Documents retrieved to support this answer</p>
                </div>

                <span class="source-count">
                  {sources.length} {sources.length === 1 ? "source" : "sources"}
                </span>
              </div>

              {#if sources.length > 0}
                <div class="source-list">
                  {#each sources as source}
                    <div class="source-card">
                      <span class="file-icon">PDF</span>

                      <div class="source-details">
                        <strong>{source.filename}</strong>
                        <span>Page {source.page}</span>
                      </div>

                      <span class="source-check" aria-label="Retrieved source">
                        ✓
                      </span>
                    </div>
                  {/each}
                </div>
              {:else}
                <p class="no-sources">
                  No source documents were returned for this answer.
                </p>
              {/if}
            </div>
          </section>
        {/if}

        
        {#if sourceContributions.length > 0}
            <section class="contributions-section">
                <div class="section-heading">
                    <div>
                        <h3>Source Contribution</h3>
                        <p>Estimated share of retrieved evidence by document</p>
                    </div>
                    <span class="section-count">
                        {sourceContributions.length} sources
                    </span>
                </div>

                <div class="contribution-list">
                    {#each sourceContributions as source}
                        <div class="contribution-item">
                            <div class="contribution-label">
                                <span class="contribution-filename">
                                    📄 {source.filename}
                                </span>
                                <strong>{source.percentage.toFixed(1)}%</strong>
                            </div>

                            <div
                                class="contribution-track"
                                role="progressbar"
                                aria-label={`Retrieval contribution from ${source.filename}`}
                                aria-valuemin={0}
                                aria-valuemax={100}
                                aria-valuenow={source.percentage}
                            >
                                <div
                                    class="contribution-fill"
                                    style={`width: ${source.percentage}%`}
                                ></div>
                            </div>
                        </div>
                    {/each}
                </div>

                <p class="contribution-note">
                    These percentages estimate each document's share of retrieved
                    evidence. They do not represent an exact percentage of the
                    generated answer.
                </p>
            </section>
        {/if}

        {#if chunks.length > 0}
            <section class="chunks-section">
                <div class="section-heading">
                    <div>
                        <h3>Retrieved Chunks</h3>
                        <p>Top passages retrieved for this question</p>
                    </div>
                    <span class="section-count">{chunks.length} chunks</span>
                </div>

                <div class="chunk-list">
                    {#each chunks as chunk}
                        <details class="chunk-card">
                            <summary class="chunk-summary">
                                <div class="chunk-summary-main">
                                    <span class="chunk-rank">#{chunk.rank}</span>

                                    <div class="chunk-summary-text">
                                        <strong>{chunk.filename}</strong>
                                        <span>
                                            Page {chunk.page} · Chunk {chunk.chunk_index}
                                        </span>
                                    </div>
                                </div>

                                <span class="chunk-distance">
                                    Distance: {chunk.distance.toFixed(4)}
                                </span>
                            </summary>

                            <div class="chunk-content">{chunk.text}</div>
                        </details>
                    {/each}
                </div>
            </section>
        {/if}


        <section class="connection-panel">
          <div class="connection-copy">
            <span class="connection-icon">⌘</span>
            <div>
              <h3>Backend connection</h3>
              <p>{backendStatus}</p>
            </div>
          </div>

          <button
            class="connection-button"
            type="button"
            onclick={checkBackend}
            disabled={loading}
          >
            {loading ? "Checking..." : "Check connection"}
          </button>
        </section>

        <details class="question-bank">
          <summary>
            <span>Demo question bank</span>
            <span class="question-bank-hint">Click to expand · copy and paste</span>
          </summary>

          {#each questionBank as group}
            <div class="question-group">
              <p class="question-group-title tone-{group.tone}">{group.label}</p>

              <ul class="question-list">
                {#each group.items as item}
                  <li class="question-row">
                    <span class="question-text">{item}</span>
                    <button
                      type="button"
                      class="copy-button"
                      onclick={() => copyQuestion(item)}
                    >
                      {copiedQuestion === item ? "Copied" : "Copy"}
                    </button>
                  </li>
                {/each}
              </ul>
            </div>
          {/each}
        </details>

        <footer>
          <span>Ticket RAG Demo</span>
          <span>Powered by document retrieval and AI</span>
        </footer>
      </section>
    </main>

    {#if pdfPreviewOpen}
        <div
            class="pdf-modal-backdrop"
            role="presentation"
            onclick={(event) => {
                if (event.target === event.currentTarget) {
                    closePdfPreview();
                }
            }}
        >
            <section
                class="pdf-modal"
                role="dialog"
                aria-modal="true"
                aria-label={`PDF preview: ${selectedPdf}`}
            >
                <header class="pdf-modal-header">
                    <strong>{selectedPdf}</strong>

                    <button
                        type="button"
                        onclick={closePdfPreview}
                        aria-label="Close PDF preview"
                    >
                        ✕
                    </button>
                </header>

                <iframe
                    title={`Preview of ${selectedPdf}`}
                    src={`${API_URL}/documents?filename=${encodeURIComponent(selectedPdf)}`}
                    class="pdf-viewer"
                ></iframe>
            </section>
        </div>
    {/if}
</div>

<style>


:global(*) {
    box-sizing: border-box;
}

:global(html) {
    min-height: 100%;
}

:global(body) {
    margin: 0;
    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    color: #18243b;
    background: #f5f7fb;
}

:global(button),
:global(textarea) {
    font: inherit;
}

/* ========================================
   MAIN APPLICATION LAYOUT
======================================== */

.app-layout {
    display: grid;
    grid-template-columns: 260px minmax(0, 1fr);
    gap: 24px;
    width: 100%;
    max-width: none;
    min-height: 100vh;
    margin: 0;
    padding: 16px 24px;
    align-items: start;
    transition: grid-template-columns 0.25s ease;
}

.app-layout:has(.document-sidebar.collapsed) {
    grid-template-columns: 48px minmax(0, 1fr);
}

/* ========================================
   DOCUMENT SIDEBAR
======================================== */

.document-sidebar {
    position: sticky;
    top: 0;
    display: flex;
    flex-direction: column;
    width: 100%;
    height: calc(100vh - 32px);
    min-height: 0;
    min-width: 0;
    padding: 8px;
    overflow: hidden;
    border-radius: 12px;
    background: #f0f2f5;
}

.document-sidebar.collapsed {
    align-items: center;
    padding: 8px 4px;
}

/* Keep collapse button visible */

.sidebar-toggle {
    position: relative;
    z-index: 2;
    display: grid;
    place-items: center;
    flex-shrink: 0;
    width: 34px;
    height: 34px;
    margin-bottom: 4px;
    padding: 0;
    border: 1px solid #e0e4eb;
    border-radius: 8px;
    background: #fff;
    color: #34415a;
    font-size: 24px;
    line-height: 1;
    cursor: pointer;
    transition: background 0.2s ease;
}

.sidebar-toggle:hover {
    background: #e8ebf1;
}

/* Documents panel fills the remaining sidebar height */

.documents-panel {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-height: 0;
    min-width: 0;
    margin-top: 8px;
    overflow: hidden;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    background: #fff;
}

.sidebar-title {
    flex-shrink: 0;
    margin: 0;
    padding: 14px;
    border-bottom: 1px solid #edf0f5;
    color: #24324b;
    font-size: 14px;
    font-weight: 700;
}

/* Independent scrollbar for the PDF list */

.documents-list {
    display: grid;
    align-content: start;
    gap: 8px;
    flex: 1;
    min-height: 0;
    padding: 12px;
    overflow-x: hidden;
    overflow-y: auto;
    overscroll-behavior: contain;
    scrollbar-width: thin;
    scrollbar-color: #c5cad3 transparent;
}

.documents-list::-webkit-scrollbar {
    width: 6px;
}

.documents-list::-webkit-scrollbar-track {
    background: transparent;
}

.documents-list::-webkit-scrollbar-thumb {
    background: #c5cad3;
    border-radius: 10px;
}

.documents-list::-webkit-scrollbar-thumb:hover {
    background: #9ca5b4;
}

/* Individual PDF card */

.document-item {
    display: grid;
    gap: 8px;
    min-width: 0;
    padding: 10px;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    background: #fff;
    transition: border-color 0.2s ease, background 0.2s ease;
}

.document-item:hover {
    border-color: #cbd5e1;
    background: #fafbff;
}

.document-filename {
    overflow-wrap: anywhere;
    color: #34415a;
    font-size: 12px;
    line-height: 1.5;
}

/* Preview button */

.preview-button {
    justify-self: start;
    padding: 7px 12px;
    border: 1px solid #d8def0;
    border-radius: 7px;
    background: #f5f7ff;
    color: #354bd0;
    font-size: 12px;
    cursor: pointer;
    transition: background 0.2s ease, border-color 0.2s ease;
}

.preview-button:hover {
    background: #e9edff;
    border-color: #bdc8ff;
}

/* ========================================
   MAIN CONTENT / FULL-WIDTH WORKSPACE
======================================== */

main {
    min-width: 0;
    min-height: 100vh;
    background:
        radial-gradient(ellipse at 50% 0%, #e8efff 0%, transparent 48%),
        #f5f7fb;
}

.topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    width: 100%;
    min-height: 76px;
    padding: 0 5%;
    border-bottom: 1px solid #e6eaf2;
    background: rgb(255 255 255 / 90%);
}

.brand {
    display: flex;
    align-items: center;
    gap: 11px;
    color: #172554;
    font-size: 19px;
    font-weight: 750;
    text-decoration: none;
}

.brand-icon {
    display: grid;
    place-items: center;
    width: 38px;
    height: 38px;
    flex-shrink: 0;
    border-radius: 12px;
    background: linear-gradient(135deg, #4f6cf7, #7454df);
    box-shadow: 0 5px 14px #5269e530;
    color: #fff;
    font-size: 13px;
}

.brand-light {
    color: #6b7890;
    font-weight: 500;
}

.demo-label {
    color: #68758d;
    font-size: 11px;
    font-weight: 750;
    letter-spacing: 1.3px;
}

/* Workspace can expand across the available width */

.workspace {
    width: 100%;
    max-width: none;
    margin: 0;
    padding: 54px clamp(20px, 5%, 80px) 28px;
}

.intro {
    width: 100%;
    max-width: 1100px;
    margin: 0 auto 28px;
    text-align: center;
}

.eyebrow {
    color: #536be6;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 1.7px;
}

.intro h1 {
    margin: 13px 0 12px;
    color: #172554;
    font-size: clamp(28px, 3vw, 40px);
    line-height: 1.15;
    letter-spacing: -1.4px;
}

.intro > p {
    max-width: 700px;
    margin: 0 auto;
    color: #68758d;
    font-size: 15px;
    line-height: 1.8;
}

/* Main question and answer cards */

.panel {
    width: 100%;
    min-width: 0;
    padding: 28px;
    border: 1px solid #e4e9f2;
    border-radius: 18px;
    background: #fff;
    box-shadow: 0 12px 35px #1b2e5910;
}

.panel-heading {
    display: flex;
    align-items: center;
    gap: 13px;
    margin-bottom: 27px;
}

.heading-icon {
    display: grid;
    place-items: center;
    width: 44px;
    height: 44px;
    flex-shrink: 0;
    border-radius: 13px;
    background: #edf0ff;
    color: #4b61dc;
    font-size: 24px;
}

h2,
h3,
p {
    overflow-wrap: anywhere;
}

.heading-copy h2,
.result-title h2 {
    margin: 0 0 5px;
    color: #172554;
    font-size: 18px;
}

.heading-copy p,
.result-title p {
    margin: 0;
    color: #7b879b;
    font-size: 13px;
}

form label {
    display: block;
    margin-bottom: 9px;
    color: #34415a;
    font-size: 13px;
    font-weight: 700;
}

textarea {
    display: block;
    width: 100%;
    min-height: 100px;
    padding: 15px;
    resize: vertical;
    outline: none;
    border: 1px solid #dce3ef;
    border-radius: 11px;
    background: #fbfcff;
    color: #26344e;
    line-height: 1.6;
    transition: border-color 0.2s, box-shadow 0.2s;
}

textarea::placeholder {
    color: #9aa5b7;
}

textarea:focus {
    border-color: #6478ee;
    box-shadow: 0 0 0 4px #6478ee1c;
}

textarea:disabled {
    opacity: 0.7;
}

.input-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-top: 13px;
}

.input-hint {
    color: #8792a5;
    font-size: 11px;
    line-height: 1.5;
}

.ask-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    min-height: 44px;
    padding: 0 18px;
    flex-shrink: 0;
    border: 0;
    border-radius: 10px;
    background: #4c61e8;
    color: #fff;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    transition: background 0.2s, transform 0.2s;
}

.ask-button:hover:not(:disabled) {
    transform: translateY(-1px);
    background: #354bd0;
}

button:disabled {
    opacity: 0.55;
    cursor: not-allowed;
}

/* Sample questions */

.suggestions {
    margin-top: 28px;
    padding-top: 22px;
    border-top: 1px solid #edf0f5;
}

.suggestion-title {
    margin: 0 0 12px;
    color: #8b96a9;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 1.2px;
}

.suggestion-list {
    display: flex;
    flex-wrap: wrap;
    gap: 9px;
}

.suggestion {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    border: 1px solid #e4e8f2;
    border-radius: 9px;
    background: #f8f9fd;
    color: #44516a;
    text-align: left;
    font-size: 12px;
    cursor: pointer;
    transition: border-color 0.2s, background 0.2s;
}

.suggestion:hover:not(:disabled) {
    border-color: #bfc9ff;
    background: #eef1ff;
}

.suggestion span {
    color: #6878dd;
}

/* Demo question bank */

.question-bank {
    margin-top: 22px;
    padding: 16px 18px;
    border: 1px solid #e4e8f2;
    border-radius: 12px;
    background: #ffffff;
}

.question-bank summary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    cursor: pointer;
    color: #1f2a44;
    font-size: 14px;
    font-weight: 700;
    list-style: none;
}

.question-bank summary::-webkit-details-marker {
    display: none;
}

.question-bank-hint {
    color: #8b96a9;
    font-size: 11px;
    font-weight: 500;
}

.question-group {
    margin-top: 18px;
}

.question-group-title {
    margin: 0 0 8px;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 1.2px;
    text-transform: uppercase;
}

.tone-in {
    color: #1f7a4d;
}

.tone-out {
    color: #a86400;
}

.tone-draft {
    color: #3a4fc7;
}

.question-list {
    margin: 0;
    padding: 0;
    list-style: none;
}

.question-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 8px 10px;
    border-bottom: 1px solid #f0f2f7;
}

.question-text {
    color: #44516a;
    font-size: 12px;
    line-height: 1.5;
    user-select: all;
}

.copy-button {
    flex-shrink: 0;
    padding: 5px 10px;
    border: 1px solid #d5dcea;
    border-radius: 7px;
    background: #f8f9fd;
    color: #44516a;
    font-size: 11px;
    cursor: pointer;
}

.copy-button:hover {
    border-color: #bfc9ff;
    background: #eef1ff;
}

/* Error and loading panels */

.error-message {
    margin-top: 22px;
    padding: 16px;
    border: 1px solid #ffdada;
    border-radius: 10px;
    background: #fff3f3;
    color: #a52b37;
}

.error-message p {
    margin: 7px 0;
    font-size: 13px;
    line-height: 1.6;
}

.retry-button {
    padding: 5px 0;
    border: 0;
    background: none;
    color: #a52b37;
    text-decoration: underline;
    cursor: pointer;
}

.loading-panel {
    display: flex;
    align-items: center;
    gap: 17px;
    margin-top: 22px;
}

.loading-panel h2 {
    margin: 0 0 7px;
    font-size: 16px;
}

.loading-panel p {
    margin: 0;
    color: #748198;
    font-size: 13px;
    line-height: 1.6;
}

.spinner,
.large-spinner {
    border: 2px solid #ffffff70;
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
}

.spinner {
    width: 14px;
    height: 14px;
}

.large-spinner {
    width: 30px;
    height: 30px;
    flex-shrink: 0;
    border-color: #e0e6ff;
    border-top-color: #5267e8;
}

@keyframes spin {
    to {
        transform: rotate(360deg);
    }
}

/* Answer panel */

.answer-panel {
    margin-top: 22px;
    animation: reveal 0.3s ease-out;
}

@keyframes reveal {
    from {
        opacity: 0;
        transform: translateY(8px);
    }

    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.result-heading,
.result-title,
.sources-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
}

.result-title {
    justify-content: flex-start;
}

.success-icon {
    display: grid;
    place-items: center;
    width: 34px;
    height: 34px;
    flex-shrink: 0;
    border-radius: 50%;
    background: #e6f8ee;
    color: #16794a;
    font-weight: 800;
}

.clear-button {
    padding: 8px 12px;
    border: 1px solid #dfe5ef;
    border-radius: 8px;
    background: #fff;
    color: #586781;
    font-size: 12px;
    cursor: pointer;
}

.clear-button:hover {
    background: #f5f7fb;
}

.answer-content {
    margin-top: 23px;
    padding: 19px;
    overflow-wrap: anywhere;
    border: 1px solid #e8edf7;
    border-radius: 11px;
    background: #f8faff;
    color: #37445c;
    font-size: 14px;
    line-height: 1.85;
}

.answer-content p {
    margin: 0;
    white-space: pre-wrap;
}

.answer-spacer {
    height: 12px;
}

/* Sources */

.sources-section {
    margin-top: 26px;
    padding-top: 22px;
    border-top: 1px solid #edf0f5;
}

.sources-heading h3 {
    margin: 0 0 5px;
    color: #24324b;
    font-size: 14px;
}

.sources-heading p {
    margin: 0;
    color: #8792a5;
    font-size: 12px;
    line-height: 1.6;
}

.source-count {
    padding: 6px 9px;
    flex-shrink: 0;
    border-radius: 20px;
    background: #edf0ff;
    color: #5365cf;
    font-size: 11px;
    font-weight: 700;
}

.source-list {
    display: grid;
    gap: 10px;
    margin-top: 17px;
}

.source-card {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 13px;
    border: 1px solid #e5eaf3;
    border-radius: 10px;
}

.file-icon {
    display: grid;
    place-items: center;
    width: 39px;
    height: 42px;
    flex-shrink: 0;
    border-radius: 8px;
    background: #fff0f0;
    color: #c3444b;
    font-size: 10px;
    font-weight: 800;
}

.source-details {
    display: flex;
    flex: 1;
    flex-direction: column;
    gap: 5px;
    min-width: 0;
}

.source-details strong {
    overflow-wrap: anywhere;
    color: #35425a;
    font-size: 12px;
}

.source-details span {
    color: #8792a5;
    font-size: 11px;
}

.source-check {
    color: #238455;
    font-weight: 800;
}

.no-sources {
    color: #748198;
    font-size: 13px;
}

/* Backend connection */

.connection-panel {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    width: 100%;
    margin-top: 22px;
    padding: 18px 20px;
    border: 1px solid #e4e9f2;
    border-radius: 14px;
    background: #fff;
}

.connection-copy {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;
}

.connection-icon {
    display: grid;
    place-items: center;
    width: 35px;
    height: 35px;
    flex-shrink: 0;
    border-radius: 10px;
    background: #edf0ff;
    color: #5368dc;
}

.connection-copy h3 {
    margin: 0 0 5px;
    color: #34415a;
    font-size: 13px;
}

.connection-copy p {
    margin: 0;
    color: #7b879b;
    font-size: 11px;
    line-height: 1.6;
}

.connection-button {
    padding: 10px 12px;
    flex-shrink: 0;
    border: 1px solid #dfe4ff;
    border-radius: 8px;
    background: #f0f2ff;
    color: #475bd3;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
}

.connection-button:hover:not(:disabled) {
    background: #e4e8ff;
}

footer {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    padding: 24px 4px 0;
    color: #929caf;
    font-size: 11px;
}

/* ========================================
   PDF PREVIEW MODAL
======================================== */

.pdf-modal-backdrop {
    position: fixed;
    inset: 0;
    z-index: 1000;
    display: grid;
    place-items: center;
    padding: 20px;
    background: rgb(15 23 42 / 65%);
}

.pdf-modal {
    display: flex;
    flex-direction: column;
    width: min(100%, 1000px);
    height: 90vh;
    overflow: hidden;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    background: #fff;
    box-shadow: 0 20px 60px rgb(15 23 42 / 25%);
}

.pdf-modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 14px 18px;
    border-bottom: 1px solid #e2e8f0;
}

.pdf-modal-header strong {
    overflow-wrap: anywhere;
    color: #24324b;
    font-size: 14px;
}

.pdf-modal-header button {
    display: grid;
    place-items: center;
    width: 32px;
    height: 32px;
    flex-shrink: 0;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    background: #fff;
    color: #34415a;
    cursor: pointer;
}

.pdf-modal-header button:hover {
    background: #f1f5f9;
}

.pdf-viewer {
    flex: 1;
    width: 100%;
    min-height: 0;
    border: 0;
    background: #f8fafc;
}

/* ========================================
   RESPONSIVE DESIGN
======================================== */

@media (max-width: 760px) {
    .app-layout,
    .app-layout:has(.document-sidebar.collapsed) {
        grid-template-columns: 42px minmax(0, 1fr);
        gap: 10px;
        padding: 12px;
    }

    .document-sidebar {
        top: 0;
        height: calc(100vh - 24px);
        padding: 5px;
    }

    .document-sidebar.collapsed {
        padding: 5px 3px;
    }

    .sidebar-toggle {
        width: 32px;
        height: 32px;
    }

    .workspace {
        padding: 32px 12px 24px;
    }

    .panel {
        padding: 20px;
        border-radius: 14px;
    }

    .pdf-modal-backdrop {
        padding: 8px;
    }

    .pdf-modal {
        width: 100%;
        height: 95vh;
        border-radius: 8px;
    }

    .pdf-modal-header {
        padding: 10px 12px;
    }
}

@media (max-width: 560px) {
    .topbar {
        min-height: 65px;
        padding: 0 14px;
    }

    .brand {
        gap: 8px;
        font-size: 16px;
    }

    .brand-icon {
        width: 34px;
        height: 34px;
    }

    .demo-label {
        font-size: 9px;
        letter-spacing: 0.6px;
    }

    .workspace {
        padding-top: 28px;
    }

    .input-footer {
        align-items: stretch;
        flex-direction: column;
    }

    .ask-button {
        width: 100%;
    }

    .connection-panel {
        align-items: stretch;
        flex-direction: column;
    }

    .connection-button {
        width: 100%;
    }

    footer {
        flex-direction: column;
    }
}

@media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
    }
}


/* ========================================
   SOURCE CONTRIBUTION
======================================== */

.contributions-section,
.chunks-section {
    width: 100%;
    min-width: 0;
    margin-top: 26px;
    padding-top: 22px;
    border-top: 1px solid #edf0f5;
}

.section-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    margin-bottom: 18px;
}

.section-heading h3 {
    margin: 0 0 5px;
    color: #24324b;
    font-size: 14px;
    font-weight: 700;
}

.section-heading p {
    margin: 0;
    color: #8792a5;
    font-size: 12px;
    line-height: 1.6;
}

.section-count {
    flex-shrink: 0;
    padding: 6px 9px;
    border-radius: 20px;
    background: #edf0ff;
    color: #5365cf;
    font-size: 11px;
    font-weight: 700;
}

/* Contribution progress bars */

.contribution-list {
    display: grid;
    gap: 18px;
}

.contribution-item {
    display: grid;
    gap: 9px;
    min-width: 0;
}

.contribution-label {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
}

.contribution-filename {
    min-width: 0;
    overflow-wrap: anywhere;
    color: #35425a;
    font-size: 12px;
}

.contribution-label strong {
    flex-shrink: 0;
    color: #354bd0;
    font-size: 12px;
}

.contribution-track {
    height: 9px;
    overflow: hidden;
    border-radius: 999px;
    background: #e9edf5;
}

.contribution-fill {
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(90deg, #6478ee, #8b6ee8);
    transition: width 0.35s ease;
}

.contribution-note {
    margin: 16px 0 0;
    color: #8792a5;
    font-size: 11px;
    line-height: 1.7;
}

/* ========================================
   RETRIEVED CHUNKS
======================================== */

.chunk-list {
    display: grid;
    gap: 10px;
}

.chunk-card {
    min-width: 0;
    overflow: hidden;
    border: 1px solid #e4e9f2;
    border-radius: 11px;
    background: #fff;
    transition: border-color 0.2s ease;
}

.chunk-card:hover {
    border-color: #cbd5e1;
}

.chunk-summary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 15px;
    cursor: pointer;
    list-style: none;
}

.chunk-summary::-webkit-details-marker {
    display: none;
}

.chunk-summary::marker {
    content: "";
}

.chunk-summary::after {
    content: "＋";
    flex-shrink: 0;
    color: #6878dd;
    font-size: 17px;
}

.chunk-card[open] .chunk-summary::after {
    content: "−";
}

.chunk-summary-main {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;
}

.chunk-rank {
    display: grid;
    place-items: center;
    width: 34px;
    height: 34px;
    flex-shrink: 0;
    border-radius: 9px;
    background: #edf0ff;
    color: #5365cf;
    font-size: 12px;
    font-weight: 800;
}

.chunk-summary-text {
    display: grid;
    gap: 5px;
    min-width: 0;
}

.chunk-summary-text strong {
    overflow-wrap: anywhere;
    color: #35425a;
    font-size: 12px;
}

.chunk-summary-text span {
    color: #8792a5;
    font-size: 11px;
}

.chunk-distance {
    flex-shrink: 0;
    color: #64748b;
    font-size: 11px;
}

.chunk-content {
    padding: 16px;
    border-top: 1px solid #edf0f5;
    background: #f8faff;
    color: #46536b;
    font-size: 13px;
    line-height: 1.8;
    overflow-wrap: anywhere;
    white-space: pre-wrap;
}

/* Responsive layout for smaller screens */

@media (max-width: 560px) {
    .section-heading {
        align-items: flex-start;
    }

    .chunk-summary {
        align-items: flex-start;
        flex-wrap: wrap;
        gap: 10px;
        padding: 12px;
    }

    .chunk-distance {
        margin-left: 46px;
    }

    .chunk-content {
        padding: 12px;
    }
}


/* ==========================================
   COMPACT TICKET RAG WORKSPACE
   Paste at the end of the existing CSS
========================================== */

/* Use screen space more efficiently */
.workspace {
    padding-top: 24px;
    padding-bottom: 16px;
}

.intro {
    margin-bottom: 18px;
}

.intro h1 {
    margin: 8px 0;
    font-size: clamp(25px, 2.2vw, 34px);
    line-height: 1.15;
}

.intro > p {
    font-size: 13px;
    line-height: 1.6;
}

/* Reduce excess space inside cards */
.panel {
    padding: 20px 22px;
    border-radius: 14px;
}

.panel-heading {
    gap: 10px;
    margin-bottom: 16px;
}

.heading-icon {
    width: 38px;
    height: 38px;
    border-radius: 10px;
    font-size: 20px;
}

.heading-copy h2,
.result-title h2 {
    font-size: 16px;
}

.heading-copy p,
.result-title p {
    font-size: 12px;
}

/* Make the question box shorter */
textarea {
    min-height: 76px;
    padding: 11px 13px;
    line-height: 1.5;
}

textarea:focus {
    box-shadow: 0 0 0 3px #6478ee1c;
}

.input-footer {
    margin-top: 9px;
}

.ask-button {
    min-height: 38px;
    padding: 0 15px;
}

/* Bring sample questions closer to the form */
.suggestions {
    margin-top: 16px;
    padding-top: 14px;
}

.suggestion-title {
    margin-bottom: 8px;
}

.suggestion-list {
    gap: 7px;
}

.suggestion {
    padding: 8px 10px;
    font-size: 11px;
}

/* Answer appears closer to the question panel */
.answer-panel {
    margin-top: 14px;
    padding: 20px 22px;
}

.result-heading {
    gap: 10px;
}

.success-icon {
    width: 30px;
    height: 30px;
}

.clear-button {
    padding: 6px 10px;
}

.answer-content {
    margin-top: 14px;
    padding: 14px 16px;
    font-size: 13px;
    line-height: 1.7;
}

/* Compact source references */
.sources-section {
    margin-top: 18px;
    padding-top: 16px;
}

.source-list {
    gap: 7px;
    margin-top: 12px;
}

.source-card {
    gap: 10px;
    padding: 9px 11px;
}

.file-icon {
    width: 32px;
    height: 35px;
}

/* Compact source contribution section */
.contributions-section,
.chunks-section {
    margin-top: 18px;
    padding-top: 16px;
}

.section-heading {
    margin-bottom: 12px;
}

.contribution-list {
    gap: 12px;
}

.contribution-item {
    gap: 6px;
}

.contribution-track {
    height: 7px;
}

.contribution-note {
    margin-top: 10px;
}

/* Retrieved chunks: compact collapsed rows */
.chunk-list {
    gap: 7px;
}

.chunk-card {
    border-radius: 9px;
}

.chunk-summary {
    gap: 10px;
    padding: 10px 12px;
}

.chunk-summary-main {
    gap: 9px;
}

.chunk-rank {
    width: 29px;
    height: 29px;
}

.chunk-content {
    padding: 12px;
    font-size: 12px;
    line-height: 1.65;
}

/* Backend status should not dominate the page */
.connection-panel {
    margin-top: 14px;
    padding: 12px 15px;
    border-radius: 11px;
}

footer {
    padding-top: 14px;
}

/* Medium screens and tablets */
@media (max-width: 760px) {
    .workspace {
        padding: 22px 12px 16px;
    }

    .panel,
    .answer-panel {
        padding: 16px;
    }

    .intro {
        margin-bottom: 16px;
    }
}

/* Small mobile screens */
@media (max-width: 560px) {
    .workspace {
        padding: 18px 10px 14px;
    }

    .intro h1 {
        font-size: 25px;
        letter-spacing: -0.6px;
    }

    .intro > p {
        font-size: 12px;
    }

    .panel,
    .answer-panel {
        padding: 14px;
        border-radius: 12px;
    }

    .panel-heading {
        margin-bottom: 14px;
    }

    .input-footer {
        gap: 8px;
    }

    .ask-button {
        min-height: 40px;
    }

    .suggestion {
        max-width: 100%;
    }

    .chunk-distance {
        margin-left: 38px;
    }

    .section-heading {
        gap: 8px;
    }
}


</style>
