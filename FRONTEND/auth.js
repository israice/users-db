(function () {
    function showAuthError(message) {
        const errorElement = document.getElementById("auth-error");
        if (!errorElement) return;
        if (!message) {
            errorElement.style.display = "none";
            errorElement.textContent = "";
            return;
        }
        errorElement.textContent = message;
        errorElement.style.display = "block";
    }

    function syncCsrfTokens(csrfTokenValue) {
        if (!csrfTokenValue) return;
        document.querySelectorAll('input[name="csrf_token"]').forEach((inputElement) => {
            inputElement.value = csrfTokenValue;
        });
    }

    async function submitAuthFormWithAjax(formElement) {
        const formData = new FormData(formElement);
        const response = await fetch("/api/auth", { method: "POST", body: formData });
        const payload = await response.json();
        syncCsrfTokens(payload.csrf_token_value);
        if (!payload.ok) {
            showAuthError(payload.error_message || "Authentication failed");
            return;
        }
        window.location.href = payload.redirect_url || "/";
    }

    function wireAuthForms() {
        document.querySelectorAll('form[action="/"]').forEach((formElement) => {
            formElement.addEventListener("submit", async (event) => {
                event.preventDefault();
                showAuthError("");
                try {
                    await submitAuthFormWithAjax(formElement);
                } catch (_error) {
                    showAuthError("Network error. Please try again.");
                }
            });
        });
    }

    function wireTabs() {
        const authTabButtons = document.querySelectorAll(".auth-tab-button");
        const authFormPanels = document.querySelectorAll(".auth-form-panel");
        if (!authTabButtons.length || !authFormPanels.length) return;

        function activateAuthPanel(targetPanelId) {
            authFormPanels.forEach((panelElement) => panelElement.classList.remove("is-active"));
            authTabButtons.forEach((buttonElement) => buttonElement.classList.remove("is-active"));
            const targetPanelElement = document.getElementById(targetPanelId);
            const activeButtonElement = document.querySelector(
                `.auth-tab-button[data-target-panel-id="${targetPanelId}"]`
            );
            if (targetPanelElement) targetPanelElement.classList.add("is-active");
            if (activeButtonElement) activeButtonElement.classList.add("is-active");
        }

        authTabButtons.forEach((buttonElement) => {
            buttonElement.addEventListener("click", () => {
                activateAuthPanel(buttonElement.dataset.targetPanelId);
            });
        });
    }

    wireTabs();
    wireAuthForms();
})();
