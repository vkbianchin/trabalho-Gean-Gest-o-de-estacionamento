/* Tela: clientes (pessoa física/jurídica, edição e ativação) */
(() => {
  "use strict";
  const P = window.ParkFlow;
  const { api, badge, catchForm, esc, fd, field, fmtDoc, maskDocumento, modal, panel, select, table, toast, wireSearch, confirmar, ehAdmin } = P;
  const $ = P.$;
  const UFS = ["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"];
  const v = x => esc(x ?? "");   // valor de campo: vazio em vez de "—"

  const fmtTelefone = d => { const n = String(d || "").replace(/\D/g, ""); return n.length === 11 ? `(${n.slice(0,2)}) ${n.slice(2,7)}-${n.slice(7)}` : n.length === 10 ? `(${n.slice(0,2)}) ${n.slice(2,6)}-${n.slice(6)}` : n; };
  const fmtCep = d => { const n = String(d || "").replace(/\D/g, ""); return n.length === 8 ? `${n.slice(0,5)}-${n.slice(5)}` : n; };

  function camposCadastrais(c = {}) {
    return `${field("Telefone","telefone","tel",true,"(00) 00000-0000",`value="${v(fmtTelefone(c.telefone))}"`)}
      ${field("E-mail (opcional)","email","email",false,"cliente@exemplo.com",`value="${v(c.email)}"`)}
      ${field("CEP","cep","text",true,"00000-000",`maxlength="9" inputmode="numeric" value="${v(fmtCep(c.cep))}"`)}
      ${field("Logradouro","logradouro","text",true,"",`value="${v(c.logradouro)}"`)}
      ${field("Número","numero","text",true,"",`value="${v(c.numero)}"`)}
      ${field("Complemento (opcional)","complemento","text",false,"Apto, bloco...",`value="${v(c.complemento)}"`)}
      ${field("Bairro","bairro","text",true,"",`value="${v(c.bairro)}"`)}
      ${field("Cidade","cidade","text",true,"",`value="${v(c.cidade)}"`)}
      <label>UF<select name="uf" required><option value="">Selecione...</option>${UFS.map(x => `<option ${x === (c.uf || "SC") ? "selected" : ""}>${x}</option>`).join("")}</select></label>
      <small class="span-2" id="cep-status"></small>`;
  }

  const acoes = r => {
    const ativo = Number(r.ativo) === 1;
    return `<button class="btn btn-secondary btn-sm" data-edit="${esc(r.id)}">Editar</button>` +
      (ehAdmin() ? ` <button class="btn ${ativo ? "btn-danger" : "btn-secondary"} btn-sm" data-toggle="${esc(r.id)}" data-ativo="${ativo ? 0 : 1}">${ativo ? "Desativar" : "Ativar"}</button>` : "");
  };

  async function clients() {
    const rows = await api("/api/clientes");
    $("#app-content").innerHTML = panel("Clientes", "Pessoas físicas e jurídicas com veículos no estacionamento",
      `<div class="toolbar"><label class="field search"><input id="search-table" placeholder="Buscar nome, CPF/CNPJ ou cidade..."></label><button class="btn btn-primary" id="new-client">＋ Novo cliente</button></div><div style="height:15px"></div><div id="table-results">${table([
        { key: "nome", label: "Nome / razão social" },
        { key: "tipo_pessoa", label: "Tipo", render: t => t === "juridica" ? "Pessoa jurídica" : "Pessoa física" },
        { key: "documento", label: "CPF / CNPJ", render: d => esc(fmtDoc(d)) },
        { key: "telefone", label: "Telefone", render: t => esc(fmtTelefone(t)) },
        { key: "email", label: "E-mail" }, { key: "cidade", label: "Cidade" },
        { key: "ativo", label: "Status", render: badge },
        { key: "id", label: "", render: (id, r) => acoes(r) },
      ], rows)}</div>`);
    wireSearch($("#search-table"), $("#table-results"));
    $("#new-client").onclick = novoCliente;
    $("#table-results").addEventListener("click", async e => {
      const editar = e.target.closest("[data-edit]"), alternar = e.target.closest("[data-toggle]");
      try {
        if (editar) await editarCliente(editar.dataset.edit);
        if (alternar) {
          const ativar = alternar.dataset.ativo === "1";
          if (!await confirmar(ativar ? "Ativar cliente" : "Desativar cliente", ativar ? "O cliente voltará a aparecer nos cadastros." : "O cliente deixa de ser usado em novos cadastros e contratos. Os dados e o histórico são mantidos.", ativar ? "Ativar" : "Desativar", !ativar)) return;
          const r = await api(`/api/clientes/${alternar.dataset.toggle}/ativo`, { method: "POST", body: JSON.stringify({ ativo: ativar }) });
          toast(r.mensagem);
          await clients();
        }
      } catch (err) { toast(err.message, "error"); }
    });
  }

  function novoCliente() {
    modal("Cadastrar cliente", `<form id="client-form" class="form-grid">
      <label>Tipo de pessoa<select name="tipo_pessoa"><option value="fisica">Pessoa física</option><option value="juridica">Pessoa jurídica</option></select></label>
      ${field("CPF","documento","text",true,"000.000.000-00",'maxlength="18" inputmode="numeric"')}
      ${field("Nome completo","nome","text",true,"",'maxlength="100"')}
      ${camposCadastrais()}
      <div class="form-actions span-2"><button type="button" class="btn btn-secondary" data-close>Cancelar</button><button class="btn btn-primary">Salvar cliente</button></div></form>`);
    const form = $("#client-form"), tipo = form.elements.tipo_pessoa, doc = form.elements.documento, nome = form.elements.nome;
    // Pessoa física x jurídica: troca rótulos, máscara e validação do documento.
    tipo.addEventListener("change", () => {
      const pj = tipo.value === "juridica";
      doc.closest("label").childNodes[0].textContent = pj ? "CNPJ" : "CPF";
      doc.placeholder = pj ? "00.000.000/0000-00" : "000.000.000-00";
      nome.closest("label").childNodes[0].textContent = pj ? "Razão social" : "Nome completo";
      doc.value = maskDocumento(doc.value, pj);
      if (doc.value) doc.dispatchEvent(new Event("blur"));
    });
    assistirEndereco(form);
    catchForm(form, async e => {
      await api("/api/clientes", { method: "POST", body: JSON.stringify(fd(e.currentTarget)) });
      $("#modal-root").innerHTML = "";
      toast("Cliente cadastrado.");
      await clients();
    });
  }

  async function editarCliente(id) {
    const c = await api(`/api/clientes/${id}`);
    const pj = c.tipo_pessoa === "juridica";
    modal("Editar cliente", `<form id="client-edit-form" class="form-grid">
      <label>${pj ? "CNPJ" : "CPF"}<input value="${v(fmtDoc(c.documento))}" disabled></label>
      ${field(pj ? "Razão social" : "Nome completo","nome","text",true,"",`maxlength="100" value="${v(c.nome)}"`)}
      ${camposCadastrais(c)}
      <small class="span-2">O CPF/CNPJ e o tipo de pessoa não podem ser alterados. Para corrigi-los, cadastre um novo cliente.</small>
      <div class="form-actions span-2"><button type="button" class="btn btn-secondary" data-close>Cancelar</button><button class="btn btn-primary">Salvar alterações</button></div></form>`);
    const form = $("#client-edit-form");
    assistirEndereco(form);
    catchForm(form, async e => {
      const r = await api(`/api/clientes/${id}`, { method: "PUT", body: JSON.stringify(fd(e.currentTarget)) });
      $("#modal-root").innerHTML = "";
      toast(r.mensagem);
      await clients();
    });
  }

  function assistirEndereco(form) {
    // Preenchimento assistido: ao digitar um CEP completo, consulta o ViaCEP e completa o endereço.
    const cep = form.elements.cep, status = $("#cep-status");
    let ultimo = "";
    cep?.addEventListener("input", async () => {
      const n = cep.value.replace(/\D/g, "");
      if (n.length !== 8 || n === ultimo) return;
      ultimo = n;
      status.textContent = "Buscando endereço...";
      try {
        const d = await (await fetch(`https://viacep.com.br/ws/${n}/json/`)).json();
        if (d.erro) { status.textContent = "CEP não encontrado. Preencha o endereço manualmente."; return; }
        const preencher = (nome, valor) => { const el = form.elements[nome]; if (el && valor && !el.value) { el.value = valor; el.dispatchEvent(new Event("input")); } };
        preencher("logradouro", d.logradouro); preencher("bairro", d.bairro); preencher("cidade", d.localidade);
        if (d.uf && form.elements.uf) form.elements.uf.value = d.uf;
        status.textContent = "Endereço preenchido. Confira os dados e informe o número.";
      } catch { status.textContent = "Não foi possível consultar o CEP agora. Preencha o endereço manualmente."; }
    });
  }

  P.telas.clientes = clients;
})();
