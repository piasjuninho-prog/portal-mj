// ==UserScript==
// @name         Robô MJ - PagBank v93.0 (CONTROLE TOTAL)
// @namespace    http://tampermonkey.net/
// @version      93.0
// @description  Carga automática de histórico, filtro de bloco e botão para interromper.
// @author       MJ Soluções
// @match        *://minhaconta.pagbank.com.br/*
// @grant        GM_xmlhttpRequest
// @grant        window.close
// @connect      oiuyklgtcazbtuvwmelv.supabase.co
// ==/UserScript==

(function() {
    'use strict';

    const DB = {
        URL: "https://oiuyklgtcazbtuvwmelv.supabase.co/rest/v1/vendas",
        KEY: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9pdXlrbGd0Y2F6YnR1dndtZWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzMTg2MjMsImV4cCI6MjA4OTg5NDYyM30.tzIPjSDlKLg5h12lbUYKt-NsYH85cP-WNiWUtGsIyKc"
    };

    // --- 1. CAPTURA NOS DETALHES (ABA FILHA) ---
    if (window.location.href.includes('detalhes') || window.location.href.includes('transacao')) {
        let check = setInterval(() => {
            const b = document.body.innerText;
            const id = b.match(/Código da transação:\s*([A-Z0-9-]+)/i)?.[1];
            const v = b.match(/Valor:\s*R\$\s*([\d.,]+)/i)?.[1] || b.match(/bruto\s*R\$\s*([\d.,]+)/i)?.[1];
            const n = b.match(/Número de série:\s*([A-Z0-9]+)/i)?.[1];
            const dataReal = b.match(/(\d{2}\/\d{2}\/\d{4})/)?.[0];

            if (id && v && n && dataReal) {
                clearInterval(check);
                let bandeira = b.toUpperCase().includes("VISA") ? "visa" : b.toUpperCase().includes("ELO") ? "elo" : "mastercard";
                let plano = b.includes("parcelado") ? "em " + (b.match(/(\d+x)/i)?.[1] || "parcelado") : "à vista";
                if (b.includes("DÉBITO")) plano = "débito";

                GM_xmlhttpRequest({
                    method: "POST", url: DB.URL,
                    headers: { "Content-Type": "application/json", "apikey": DB.KEY, "Authorization": "Bearer "+DB.KEY, "Prefer": "resolution=merge-duplicates" },
                    data: JSON.stringify({
                        "ns": n, "terminal": n, "adquirente": "PagBank", "status_pagamento": "Aprovada",
                        "bruto": parseFloat(v.replace(/\./g, '').replace(',', '.')),
                        "data_venda": dataReal, "taxa_label": id, "bandeira": bandeira, "plano": plano
                    }),
                    onload: () => window.close()
                });
            }
        }, 1500);
        return;
    }

    // --- 2. INTERFACE DE CONTROLE ---
    const gui = document.createElement("div");
    gui.style = "position:fixed;top:10px;right:10px;z-index:99999;background:#fff;padding:15px;border-radius:12px;border:3px solid #007bff;width:240px;text-align:center;box-shadow:0 10px 30px rgba(0,0,0,0.3);font-family:sans-serif;";
    
    let isRunning = localStorage.getItem("mj_sync_active") === "true";

    gui.innerHTML = `
        <b style="color:#007bff;">MJ PRO CONTROL v93</b><br>
        <input type="date" id="mj-dt" style="width:90%;margin:10px 0;padding:8px;border:1px solid #ccc;border-radius:8px;">
        <button id="mj-start" style="width:100%;padding:10px;background:#28a745;color:white;border:none;border-radius:8px;font-weight:bold;cursor:pointer;display:${isRunning?'none':'block'}">▶ INICIAR SYNC</button>
        <button id="mj-stop" style="width:100%;padding:10px;background:#dc3545;color:white;border:none;border-radius:8px;font-weight:bold;cursor:pointer;display:${isRunning?'block':'none'}">⏹ PARAR AGORA</button>
        <div id="mj-st" style="font-size:11px;margin-top:10px;color:#333;font-weight:bold;background:#f8f9fa;padding:8px;border-radius:8px;min-height:30px;">Aguardando...</div>
    `;
    document.body.appendChild(gui);

    const inputData = document.getElementById("mj-dt");
    const status = document.getElementById("mj-st");
    inputData.value = localStorage.getItem("mj_saved_date") || new Date().toISOString().split('T')[0];

    document.getElementById("mj-start").onclick = () => {
        localStorage.setItem("mj_sync_active", "true");
        localStorage.setItem("mj_saved_date", inputData.value);
        location.reload();
    };

    document.getElementById("mj-stop").onclick = () => {
        localStorage.setItem("mj_sync_active", "false");
        location.reload();
    };

    // --- 3. MOTOR DE PROCESSAMENTO ---
    if (isRunning) {
        setTimeout(async () => {
            const d = inputData.value.split("-");
            const months = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
            const labelTarget = `${d[2]} ${months[parseInt(d[1]) - 1]} ${d[0]}`; 
            
            // FASE 1: AUTO-LOADER (ABRE O HISTÓRICO ATÉ ACHAR O DIA SELECIONADO)
            let foundData = false;
            for(let i=0; i<15; i++) {
                status.innerText = `📥 Carregando itens... (${i+1}/15)`;
                if (document.body.innerText.includes(labelTarget)) { foundData = true; break; }
                window.scrollTo(0, document.body.scrollHeight);
                let btnLoad = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes("Carregar mais itens"));
                if (btnLoad) { btnLoad.click(); await new Promise(r => setTimeout(r, 4000)); }
                else { break; }
            }

            if (!foundData) { status.innerText = "❌ Data não encontrada no histórico."; localStorage.setItem("mj_sync_active", "false"); return; }

            // FASE 2: FILTRAGEM POR BLOCO (IDENTIFICA O DIA)
            const allElements = Array.from(document.querySelectorAll('*'));
            const header = allElements.find(el => el.innerText && el.innerText.trim() === labelTarget);
            const startY = header.getBoundingClientRect().top + window.scrollY;

            // Busca o próximo cabeçalho (dia anterior) para limitar o fim do bloco
            const nextHeader = allElements.find(el => 
                el.innerText && /^\d{2}\s[A-Za-z]{3}\s\d{4}$/.test(el.innerText.trim()) && 
                (el.getBoundingClientRect().top + window.scrollY) > startY + 150
            );
            const endY = nextHeader ? (nextHeader.getBoundingClientRect().top + window.scrollY + 50) : 9999999;

            let sales = Array.from(document.querySelectorAll('div, a')).filter(el => {
                const y = el.getBoundingClientRect().top + window.scrollY;
                return el.innerText.includes("APROVADA") && el.innerText.includes("R$") && y > startY && y < endY && el.offsetHeight > 40;
            });

            status.innerText = `✅ Encontradas ${sales.length} vendas. Iniciando...`;
            await new Promise(r => setTimeout(r, 2000));

            // FASE 3: CICLO DE SINCRONIZAÇÃO
            for (let i = 0; i < sales.length; i++) {
                // Checa se o usuário mandou parar
                if (localStorage.getItem("mj_sync_active") === "false") break;

                status.innerText = `🔄 Processando ${i+1}/${sales.length}`;
                sales[i].scrollIntoView({ block: 'center' });
                await new Promise(r => setTimeout(r, 1500));
                
                // Abre a venda
                sales[i].click();
                
                // Busca o botão Mais Detalhes
                let btnMais = null;
                for(let t=0; t<10; t++) {
                    btnMais = Array.from(document.querySelectorAll('button, a, span')).find(e => e.innerText && e.innerText.includes("Mais detalhes"));
                    if (btnMais) break;
                    await new Promise(r => setTimeout(r, 1000));
                }

                if (btnMais) {
                    btnMais.click();
                    await new Promise(r => setTimeout(r, 18000)); // Tempo para aba processar e fechar
                } else {
                    window.dispatchEvent(new KeyboardEvent('keydown', {'key':'Escape'}));
                    await new Promise(r => setTimeout(r, 1000));
                }
            }
            status.innerText = "🏁 Sincronização Concluída!";
            localStorage.setItem("mj_sync_active", "false");
        }, 5000);
    }
})();
