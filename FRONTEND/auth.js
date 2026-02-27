(function () {
    function showAuthError(message) {
        const errorElement = document.getElementById("auth-error");
        if (!errorElement) return;
        if (!message) {
            errorElement.hidden = true;
            errorElement.textContent = "";
            return;
        }
        errorElement.textContent = message;
        errorElement.hidden = false;
    }

    function syncCsrfTokens(csrfTokenValue) {
        if (!csrfTokenValue) return;
        document.querySelectorAll('input[name="csrf_token"]').forEach((inputElement) => {
            inputElement.value = csrfTokenValue;
        });
    }

    function setFormBusy(formElement, isBusy) {
        formElement.setAttribute("aria-busy", isBusy ? "true" : "false");
        formElement.querySelectorAll('button[type="submit"], button:not([type])').forEach((buttonElement) => {
            buttonElement.disabled = isBusy;
        });
    }

    async function parseAuthResponse(response) {
        const contentType = response.headers.get("content-type") || "";
        if (!contentType.includes("application/json")) return null;
        try {
            return await response.json();
        } catch (_error) {
            return null;
        }
    }

    async function submitAuthFormWithAjax(formElement) {
        const formData = new FormData(formElement);
        const response = await fetch("/api/auth", { method: "POST", body: formData });
        const payload = await parseAuthResponse(response);
        if (payload && payload.csrf_token_value) {
            syncCsrfTokens(payload.csrf_token_value);
        }

        if (!payload) {
            showAuthError(`Request failed (${response.status}). Please try again.`);
            return;
        }

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
                if (formElement.dataset.submitting === "true") return;
                formElement.dataset.submitting = "true";
                setFormBusy(formElement, true);
                showAuthError("");
                try {
                    await submitAuthFormWithAjax(formElement);
                } catch (_error) {
                    showAuthError("Network error. Please try again.");
                } finally {
                    formElement.dataset.submitting = "false";
                    setFormBusy(formElement, false);
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
