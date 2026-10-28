<script>
  import { PUBLIC_API_URL } from '$env/static/public';
  let backendStatus = $state("Not checked yet");
  let loading = $state(false);
  let question = $state("");
  let answer = $state("");
  let sources = $state([]);
  let asking = $state(false);
  let askError = $state("");

  const sampleQuestions = [
    "How can a user reset their password?",
    "What is the refund policy?",
    "How can I troubleshoot login issues?"
  ];

  async function checkBackend() {
    loading = true;

    try {
      const response = await fetch(`${PUBLIC_API_URL}/health`);

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

  function useSampleQuestion(sample) {
    question = sample;
    askError = "";
  }

  function clearConversation() {
    question = "";
    answer = "";
    sources = [];
    askError = "";
  }

  async function askQuestion() {
    if (!question.trim() || asking) return;

    asking = true;
    answer = "";
    sources = [];
    askError = "";

    try {
      const response = await fetch(`${PUBLIC_API_URL}/ask`, {
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

    <footer>
      <span>Ticket RAG Demo</span>
      <span>Powered by document retrieval and AI</span>
    </footer>
  </section>
</main>

<style>
  :global(*) {
    box-sizing: border-box;
  }

  :global(body) {
    margin: 0;
    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI",
      sans-serif;
    color: #18243b;
    background: #f5f7fb;
  }

  :global(button),
  :global(textarea) {
    font: inherit;
  }

  main {
    min-height: 100vh;
    background:
      radial-gradient(ellipse at 50% 0%, #e8efff 0%, transparent 48%),
      #f5f7fb;
  }

  .topbar {
    min-height: 76px;
    padding: 0 7%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    background: rgba(255, 255, 255, 0.9);
    border-bottom: 1px solid #e6eaf2;
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
    width: 38px;
    height: 38px;
    display: grid;
    place-items: center;
    color: white;
    background: linear-gradient(135deg, #4f6cf7, #7454df);
    border-radius: 12px;
    font-size: 13px;
    box-shadow: 0 5px 14px #5269e530;
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

  .workspace {
    width: min(100% - 32px, 790px);
    margin: 0 auto;
    padding: 54px 0 28px;
  }

  .intro {
    margin-bottom: 28px;
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
    font-size: clamp(28px, 5vw, 40px);
    line-height: 1.15;
    letter-spacing: -1.4px;
  }

  .intro > p {
    max-width: 590px;
    margin: 0 auto;
    color: #68758d;
    font-size: 15px;
    line-height: 1.8;
  }

  .panel {
    padding: 28px;
    background: white;
    border: 1px solid #e4e9f2;
    border-radius: 18px;
    box-shadow: 0 12px 35px #1b2e5910;
  }

  .panel-heading {
    display: flex;
    align-items: center;
    gap: 13px;
    margin-bottom: 27px;
  }

  .heading-icon {
    width: 44px;
    height: 44px;
    display: grid;
    place-items: center;
    flex-shrink: 0;
    color: #4b61dc;
    background: #edf0ff;
    border-radius: 13px;
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
    font-size: 18px;
    color: #172554;
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
    color: #26344e;
    background: #fbfcff;
    border: 1px solid #dce3ef;
    border-radius: 11px;
    outline: none;
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
    min-height: 44px;
    padding: 0 18px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    flex-shrink: 0;
    color: white;
    background: #4c61e8;
    border: 0;
    border-radius: 10px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 700;
    transition: background 0.2s, transform 0.2s;
  }

  .ask-button:hover:not(:disabled) {
    background: #354bd0;
    transform: translateY(-1px);
  }

  button:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }

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
    padding: 10px 12px;
    display: flex;
    align-items: center;
    gap: 10px;
    color: #44516a;
    background: #f8f9fd;
    border: 1px solid #e4e8f2;
    border-radius: 9px;
    text-align: left;
    font-size: 12px;
    cursor: pointer;
    transition: border-color 0.2s, background 0.2s;
  }

  .suggestion:hover:not(:disabled) {
    background: #eef1ff;
    border-color: #bfc9ff;
  }

  .suggestion span {
    color: #6878dd;
  }

  .error-message {
    margin-top: 22px;
    padding: 16px;
    color: #a52b37;
    background: #fff3f3;
    border: 1px solid #ffdada;
    border-radius: 10px;
  }

  .error-message p {
    margin: 7px 0;
    font-size: 13px;
    line-height: 1.6;
  }

  .retry-button {
    padding: 5px 0;
    color: #a52b37;
    background: none;
    border: none;
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
    width: 34px;
    height: 34px;
    display: grid;
    place-items: center;
    flex-shrink: 0;
    color: #16794a;
    background: #e6f8ee;
    border-radius: 50%;
    font-weight: 800;
  }

  .clear-button {
    padding: 8px 12px;
    color: #586781;
    background: white;
    border: 1px solid #dfe5ef;
    border-radius: 8px;
    font-size: 12px;
    cursor: pointer;
  }

  .clear-button:hover {
    background: #f5f7fb;
  }

  .answer-content {
    margin-top: 23px;
    padding: 19px;
    color: #37445c;
    background: #f8faff;
    border: 1px solid #e8edf7;
    border-radius: 11px;
    font-size: 14px;
    line-height: 1.85;
    overflow-wrap: anywhere;
  }

  .answer-content p {
    margin: 0;
    white-space: pre-wrap;
  }

  .answer-spacer {
    height: 12px;
  }

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
    color: #5365cf;
    background: #edf0ff;
    border-radius: 20px;
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
    width: 39px;
    height: 42px;
    display: grid;
    place-items: center;
    flex-shrink: 0;
    color: #c3444b;
    background: #fff0f0;
    border-radius: 8px;
    font-size: 10px;
    font-weight: 800;
  }

  .source-details {
    min-width: 0;
    display: flex;
    flex: 1;
    flex-direction: column;
    gap: 5px;
  }

  .source-details strong {
    color: #35425a;
    font-size: 12px;
    overflow-wrap: anywhere;
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

  .connection-panel {
    margin-top: 22px;
    padding: 18px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    background: #fff;
    border: 1px solid #e4e9f2;
    border-radius: 14px;
  }

  .connection-copy {
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .connection-icon {
    width: 35px;
    height: 35px;
    display: grid;
    place-items: center;
    flex-shrink: 0;
    color: #5368dc;
    background: #edf0ff;
    border-radius: 10px;
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
    color: #475bd3;
    background: #f0f2ff;
    border: 1px solid #dfe4ff;
    border-radius: 8px;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
  }

  .connection-button:hover:not(:disabled) {
    background: #e4e8ff;
  }

  footer {
    padding: 24px 4px 0;
    display: flex;
    justify-content: space-between;
    gap: 12px;
    color: #929caf;
    font-size: 11px;
  }

  @media (max-width: 560px) {
    .topbar {
      min-height: 65px;
      padding: 0 18px;
    }

    .brand {
      font-size: 16px;
    }

    .demo-label {
      font-size: 9px;
      letter-spacing: 0.6px;
    }

    .workspace {
      padding-top: 36px;
    }

    .panel {
      padding: 20px;
      border-radius: 14px;
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
</style>
