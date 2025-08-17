# 🧠 Chain-of-Thought Prompting

Este script implementa a técnica de **Chain-of-Thought (CoT) Prompting**, utilizada para incentivar modelos de linguagem a **explicarem seu raciocínio passo a passo** antes de fornecerem a resposta final.  

---

## 📂 Estrutura do Script

- **Entrada**  
  - Um texto ou pergunta é enviado ao modelo junto com um *prompt* especial, instruindo-o a **raciocinar em etapas**.  

- **Processamento**  
  - O modelo não apenas gera a resposta, mas também descreve seu **raciocínio intermediário**.  
  - Esse raciocínio pode ser exibido ou filtrado antes da resposta final.  

- **Saída**  
  - A resposta final do modelo.  
  - (Opcional) O raciocínio detalhado gerado no processo.  

---

## 🧩 Objetivo do Script

- Mostrar como a técnica de **Chain-of-Thought** pode:  
  - Melhorar a **precisão em tarefas complexas**.  
  - Ajudar em **explicabilidade** (entender como o modelo chegou na resposta).  
  - Apoiar o processo de **validação em experimentos com LLMs**.  

---

## 📊 Exemplo Simplificado

**Pergunta:**  
> Qual é a soma dos números de 1 a 10?

**Saída (CoT):**  
- Passo 1: Reconhecer que é uma progressão aritmética.  
- Passo 2: Calcular n(n+1)/2 para n=10.  
- Passo 3: 10*11/2 = 55.  
- **Resposta final:** 55  

---

## 📌 Observação

O uso de **Chain-of-Thought Prompting** foi aplicado neste projeto para tarefas de **extração e interpretação em textos jurídicos**, de forma a aumentar a **transparência** e a **confiabilidade** dos resultados.
