// ==UserScript==
// @name         Robô MJ - PagBank v122.1 (DATA FIX)
// @namespace    http://tampermonkey.net/
// @version      122.1
// @description  Sincronização com data dinâmica baseada no calendário selecionado.
// @author       MJ Soluções
// @match        *://minhaconta.pagbank.com.br/*
// @grant        GM_xmlhttpRequest
// @grant        window.close
// @connect      oiuyklgtcazbtuvwmelv.supabase.co
// ==/UserScript==

(function() {
    'use strict';
    let emExecucao = false;

    const DB = {
        URL: "https://oiuyklgtcazbtuvwmelv.supabase.co/rest/v1/vendas",
        KEY: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc"
    };

    // --- 1. LÓGICA DE CAPTURA (DENTRO DA ABA DE DETALHES) ---
    if (window.location.href.includes('detalhes') || window.location.href.includes('transacao')) {
        let checkData = setInterval(() => {
            const body = document.body.innerText;
            const id = body.match(/Código da transação:\s*([A-Z0-9-]+)/i)?.[1];
            const v = body.match(/Valor:\s*R\$\s*([\d.,]+)/i)?.[1] || body.match(/bruto\s*R\$\s*([\d.,]+)/i)?.[1];
            const n = body.match(/Número de série:\s*([A-Z0-9]+)/i)?.[1];
            
            // Tenta ler a data do comprovante, se não achar, usa a que o usuário escolheu no calendário
            const dtNoComprovante = body.match(/(\d{2}\/\d{2}\/\d{4})/)?.[0];
            const dtSelecionada = localStorage.getItem("mj_data_venda_ativa");

            if (id && v && n) {
                clearInterval(checkData);
                
                let bUpper = body.toUpperCase();
                let bandeira = "mastercard"; 
                if (bUpper.includes("ELO")) bandeira = "elo";
                else if (bUpper.includes("VISA")) bandeira = "visa";

                let plano = body.includes("parcelado") ? "em " + (body.match(/(\d+x)/i)?.[1] || "parcelado") : "à vista";
                if (body.includes("DÉBITO")) plano = "débito";

                GM_xmlhttpRequest({
                    method: "POST", url: DB.URL + "?on_conflict=taxa_label",
                    headers: { "Content-Type": "application/json", "apikey": DB.KEY, "Authorization": "Bearer "+DB.KEY, "Prefer": "resolution=merge-duplicates" },
                    data: JSON.stringify({
                        "ns": n, "terminal": n, "adquirente": "PagBank", "status_pagamento": "Aprovada",
                        "bruto": parseFloat(v.replace(/\./g, '').replace(',', '.')),
                        "data_venda": dtNoComprovante || dtSelecionada, // PRIORIDADE PARA A DATA REAL
                        "taxa_label": id, "bandeira": bandeira, "plano": plano
                    }),
                    onload: () => { window.close(); }
                });
            }
        }, 1500);
        return;
    }

    // --- 2. INTERFACE COM CALENDÁRIO ---
    const gui = document.createElement("div");
    gui.style = "position:fixed;top:10px;right:10px;z-index:99999;background:#fff;padding:15px;border-radius:12px;border:3px solid #28a745;width:230px;text-align:center;box-shadow:0 10px 30px rgba(0,0,0,0.3);font-family:sans-serif;";
    gui.innerHTML = `
        <b style="color:#28a745;font-size:15px;">MJ SYNC v122.1</b><br>
        <input type="date" id="mj-dt" style="width:90%;margin:10px 0;padding:8px;border:1px solid #ccc;border-radius:5px;">
        <button id="mj-go" style="width:100%;padding:12px;background:#28a745;color:white;border:none;border-radius:10px;font-weight:bold;cursor:pointer;">🚀 INICIAR SINCRONIZAÇÃO</button>
        <div id="mj-st" style="font-size:11px;margin-top:10px;color:#333;font-weight:bold;">Aguardando...</div>
    `;
    document.body.appendChild(gui);

    // Recupera a última data usada ou coloca dia 08 como padrão para o seu teste
    document.getElementById("mj-dt").value = localStorage.getItem("mj_input_cache") || "2026-08-08";

    document.getElementById("mj-go").onclick = async () => {
        const inputData = document.getElementById("mj-dt").value;
        const d = inputData.split("-");
        const dataBR = `${d[2]}/${d[1]}/${d[0]}`; // Formato 08/08/2026
        
        localStorage.setItem("mj_data_venda_ativa", dataBR);
        localStorage.setItem("mj_input_cache", inputData);

        const status = document.getElementById("mj-st");
        let sales = Array.from(document.querySelectorAll('div, a')).filter(el => 
            el.innerText && el.innerText.includes("APROVADA") && el.innerText.includes("R$") && el.offsetHeight > 40
        );

        if (sales.length === 0) { alert("Nenhuma venda carregada na tela. Role a página."); return; }

        status.innerText = `🚀 Sincronizando ${sales.length} vendas...`;

        for (let i = 0; i < sales.length; i++) {
            sales[i].scrollIntoView({ block: 'center' });
            await new Promise(r => setTimeout(r, 1200));
            sales[i].click();
            await new Promise(r => setTimeout(r, 4500));
            let btnMais = Array.from(document.querySelectorAll('button, a, span')).find(e => e.innerText && e.innerText.includes("Mais detalhes"));
            if (btnMais) {
                btnMais.click();
                await new Promise(r => setTimeout(r, 18000));
            } else {
                window.dispatchEvent(new KeyboardEvent('keydown', {'key':'Escape'}));
            }
        }
        status.innerText = "🏁 Concluído!";
    };
})();
