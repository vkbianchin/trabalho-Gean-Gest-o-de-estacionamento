
function validationMessage(el) {
  const v = el.value.trim();
  const name = (el.name || "").toLowerCase();
  const label =
    el.closest("label")?.childNodes?.[0]?.textContent?.trim() ||
    el.getAttribute("aria-label") ||
    name ||
    "Este campo";

  if (!v) {
    return el.required
      ? `${label}: este campo é obrigatório.`
      : "";
  }

  if (name === "cpf") {
    const digits = v.replace(/\D/g, "");

    if (digits.length < 11) {
      return "Digite os 11 números do CPF.";
    }

    if (!cpfValido(v)) {
      return "CPF inválido. Confira os números digitados.";
    }
  }

  if (name === "cep") {
    const digits = v.replace(/\D/g, "");

    if (digits.length !== 8) {
      return "CEP deve conter 8 números.";
    }
  }

  if (name === "telefone") {
    const digits = v.replace(/\D/g, "");

    if (digits.length < 10 || digits.length > 11) {
      return "Telefone deve ter DDD e 10 ou 11 números.";
    }
  }

  if (el.type === "email") {
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) {
      return "Digite um e-mail válido.";
    }
  }

  if (name === "placa") {
    const placa = v.replace(/[^A-Z0-9]/gi, "").toUpperCase();

    if (placa.length < 7) {
      return "Digite os 7 caracteres da placa.";
    }

    if (!/^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$/.test(placa)) {
      return "Placa inválida. Use ABC1234 ou ABC1D23.";
    }
  }

  if (el.type === "number") {
    const n = Number(v);
    const min = el.min !== "" ? Number(el.min) : null;
    const max = el.max !== "" ? Number(el.max) : null;

    if (!Number.isFinite(n)) {
      return "Digite um número válido.";
    }

    if (min !== null && n < min) {
      return `O valor mínimo é ${min}.`;
    }

    if (max !== null && n > max) {
      return `O valor máximo é ${max}.`;
    }
  }

  if (el.minLength > 0 && v.length < el.minLength) {
    return `Digite pelo menos ${el.minLength} caracteres.`;
  }

  if (el.maxLength > 0 && v.length > el.maxLength) {
    return `Digite no máximo ${el.maxLength} caracteres.`;
  }

  return "";
}


function enableLiveValidation(form) {
  if (!form || form.dataset.liveValidation === "true") return;

  form.dataset.liveValidation = "true";

  form.querySelectorAll("input, select, textarea").forEach(el => {
    const formatField = () => {
      if (el.name === "cpf") {
        const n = el.value.replace(/\D/g, "").slice(0, 11);

        el.value = n
          .replace(/(\d{3})(\d)/, "$1.$2")
          .replace(/(\d{3})(\d)/, "$1.$2")
          .replace(/(\d{3})(\d{1,2})$/, "$1-$2");
      } else if (el.name === "cep") {
        const n = el.value.replace(/\D/g, "").slice(0, 8);
        el.value = n.length > 5
          ? n.slice(0, 5) + "-" + n.slice(5)
          : n;
      } else if (el.name === "telefone") {
        const n = el.value.replace(/\D/g, "").slice(0, 11);

        if (n.length > 10) {
          el.value = n.replace(
            /(\d{2})(\d{5})(\d{4})/,
            "($1) $2-$3"
          );
        } else if (n.length > 6) {
          el.value = n.replace(
            /(\d{2})(\d{4})(\d{0,4})/,
            "($1) $2-$3"
          );
        } else if (n.length > 2) {
          el.value = n.replace(/(\d{2})(\d+)/, "($1) $2");
        } else {
          el.value = n;
        }
      } else if (el.name === "placa") {
        el.value = el.value
          .toUpperCase()
          .replace(/[^A-Z0-9]/g, "")
          .slice(0, 7);
      }
    };

    // Valida enquanto o usuário digita.
    el.addEventListener("input", () => {
      formatField();
      validateField(el, true);
    });

    // Valida também ao sair do campo.
    el.addEventListener("blur", () => {
      validateField(el, true);
    });

    // Valida quando um select muda.
    el.addEventListener("change", () => {
      validateField(el, true);
    });
  });

  // Impede o envio se houver campos inválidos.
  form.addEventListener("submit", e => {
    let firstInvalid = null;

    form.querySelectorAll("input, select, textarea").forEach(el => {
      if (!validateField(el, true) && !firstInvalid) {
        firstInvalid = el;
      }
    });

    if (firstInvalid) {
      e.preventDefault();
      e.stopImmediatePropagation();
      firstInvalid.focus();
    }
  }, true);
}

