/*
 * Château Collective — Custom JavaScript
 *
 * All behaviour lives in this self-hosted file: the CSP is script-src 'self'
 * with no 'unsafe-inline', so inline handlers (onclick/onsubmit) never run.
 */

// Confirmation guard for destructive forms: <form data-confirm="message">.
document.addEventListener("submit", function (event) {
    var form = event.target.closest("form[data-confirm]");
    if (form && !window.confirm(form.getAttribute("data-confirm"))) {
        event.preventDefault();
    }
});
