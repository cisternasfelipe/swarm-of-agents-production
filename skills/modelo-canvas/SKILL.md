---
name: creador_modelo_canvas
description: Activa esta habilidad obligatoriamente cuando el usuario busque estructurar, organizar o definir un modelo de negocios o emprendimiento. Disparadores explícitos incluyen frases como "quiero hacer un modelo canvas", "propuesta de valor", "socios clave", "actividades clave", "recursos clave", "costes de estructura", "ingresos", "canales", "relación con clientes" y "segmento de clientes". Úsala siempre para evaluar la viabilidad estratégica y comercial de una empresa o proyecto nuevo. Si el contexto exige diseñar la lógica de cómo una organización crea, entrega y captura valor, esta skill debe ejecutarse inmediatamente sin excepciones para guiarlo.
---
# Instrucciones

## Flujo de Trabajo
1. Solicita información del negocio.
2. Ajusta profundidad: Poca info (20-40 palabras), Media (40-60), Mucha (sin límite).

## Directrices de Evaluación por Bloque

### 1. Segmentos de Clientes
- **Regla de Diferenciación:** Solo separa segmentos si exigen ofertas, canales, relaciones, rentabilidades o disposición de pago distintas (Osterwalder & Pigneur). Si reaccionan igual, agrúpalos.
- **Criterio de Ajuste (Fit):** Exige validar que el producto alivie *Frustraciones*, cree *Alegrías*, facilite *Trabajos del Cliente* (Jobs to be Done) y que exista capacidad real de pago (Blank).
### 2. Propuesta de Valor
- **Enfoque de Solución:** Vende la solución al problema o "trabajo de alto valor", no especificaciones técnicas aisladas.
- **Alineación 1:1:** Cada propuesta debe conectar obligatoriamente con un segmento de clientes específico.
- **Simetría y Viabilidad:** Aliviadores y creadores deben reflejar exactamente las frustraciones y alegrías del cliente, respaldados operativamente por el lado izquierdo del lienzo.
### 3. Canales
- **Ciclo de 5 Fases:** El canal debe cubrir cronológicamente: Información, Evaluación, Compra, Entrega y Posventa.
- **Criterios de Efectividad:** Exige alineación con las preferencias del segmento, fluidez omnicanal y viabilidad financiera (el canal no debe devorar el margen).
### 4. Relación con Clientes
- **Motivación Estratégica:** Debe estar diseñada explícitamente para captación, retención o estimulación de ventas (upselling).
- **Tipología Oficial:** Clasificar en asistencia personal (exclusiva o normal), autoservicio, servicios automáticos, comunidades o co-creación.
- **Criterios de Efectividad:** Exige coherencia de expectativas con el segmento, sostenibilidad financiera y una integración nativa con los canales.
### 5. Flujo de Ingresos
- **Naturaleza y Mecanismo:** Clasificar obligatoriamente como transaccional o recurrente, y definir si usa precios fijos o dinámicos.
- **Criterios de Efectividad:** Debe coincidir con la disposición de pago, capturar valor proporcionalmente y superar la estructura de costos.
### 6. Recursos Clave
- **Categorías Oficiales:** Clasificar obligatoriamente en Físicos, Intelectuales, Humanos o Financieros.
- **Indispensabilidad:** Omitir recursos genéricos; listar solo aquellos cuya ausencia destruya la ventaja competitiva.
- **Criterios de Efectividad:** Exige alineación operativa con la propuesta, defendibilidad (difíciles de copiar) y coherencia de externalización.
### 7. Actividades Clave
- **Clasificación Core:** Enmarcar en Producción, Resolución de Problemas (ej. diseño de protocolos de seguridad integrales) o Plataforma/Red (ej. desarrollo iterativo de front-end y bases de datos).
- **Filtro Estratégico:** Excluir acciones administrativas rutinarias; conservar únicamente procesos críticos cuya suspensión detenga el modelo.
- **Criterios de Efectividad:** Validar el ajuste de transformación operativa, la escalabilidad y la coherencia interna (Make or Buy).
### 8. Estructura de Costes
- **Trazabilidad Total:** Cada gasto listado debe derivar estrictamente de un recurso, actividad o socio clave (ej. mensualidades de Claude Pro, infraestructura de hosting en Supabase, o consumo de API de OpenAI).
- **Orientación Estratégica:** Exigir definición explícita: guiado por costes (automatización masiva) o guiado por valor (creación premium).
- **Taxonomía:** Desglosar formalmente en costes fijos, variables, economías de escala o de alcance.
- **Criterios de Efectividad:** Sostenibilidad del margen unitario, coherencia absoluta con la promesa de valor y demostración de escalabilidad (Break-even Awareness).
### 9. Socios Clave
- **Tipología y Motivación:** Clasificar en alianza estratégica, coopetencia, joint venture o cliente-proveedor (ej. proveedores de APIs externas o acuerdos de alojamiento en la nube). Justificar explícitamente si buscan optimizar recursos, reducir riesgos o adquirir capacidades tecnológicas particulares.
- **Criterio de Efectividad (Core vs Non-Core):** Validar que la externalización se centre en procesos secundarios, protegiendo siempre el núcleo competitivo del negocio. Exigir que la alianza brinde reciprocidad operativa y blinde la promesa de valor frente a vulnerabilidades.

## Formato de Salida Esperado (LaTeX)
El resultado final DEBE ser código fuente LaTeX puro, listo para compilar en PDF.

### Reglas Críticas de Sintaxis LaTeX
- **Escapar caracteres especiales:** Siempre debes escapar los siguientes símbolos para evitar errores de compilación: `%` → `\%`, `$` → `\$`, `&` → `\&`, `#` → `\#`, `_` → `\_`.
- **Caracteres angulares:** `<` y `>` NO son válidos en modo texto. Renderizan como ¡ o ¿. Usa `\textless` o `\textgreater`.
- **Estructura de bloques:** Utiliza `\subsection*{Nombre del Bloque}` y entornos `\begin{itemize}[leftmargin=*]` para detallar cada punto.

### Plantilla Base Obligatoria
```latex
\documentclass{article}
% Made by Christopher Kaba
% Adapted from Florian Minges' adaptation of Alejandro Ochoa's Grant Model Canvas:
% [https://github.com/OchoaLab/grantModelCanvas](https://github.com/OchoaLab/grantModelCanvas)

% His notes regarding inspiration for the code:
%       adapted "business" version from latex code:
%       [https://rememberthecmd.blogspot.com/2015/02/draw-business-model-generation-canvas.html](https://rememberthecmd.blogspot.com/2015/02/draw-business-model-generation-canvas.html)
%       and the "grant" version (not latex):
%       [https://gregglab.neuro.utah.edu/2018/10/30/the-grant-model-canvas-for-developing-great-grants/](https://gregglab.neuro.utah.edu/2018/10/30/the-grant-model-canvas-for-developing-great-grants/)


%%%%%%%%%%%%%%%%%%%%%%%%
%%%% DOCUMENT START %%%%
%%%%%%%%%%%%%%%%%%%%%%%%

\usepackage[landscape,margin=0in]{geometry}
%\usepackage[english]{babel}
\usepackage[utf8]{inputenc}
\pagenumbering{gobble} % supress page numbers
\usepackage{hyperref}
% Sans-serif fonts
\renewcommand{\rmdefault}{phv}
\renewcommand{\sfdefault}{phv} 

\usepackage{tikz}

\title{\vspace{-2em}Sustainable Business Model Canvas}
\date{}
\author{}

\begin{document}
\maketitle

\vspace{-5em}
\centering
\def\layersep{9.7em}
\def\layerwidth{75em}

\makebox[\textwidth][c]{
  \begin{tikzpicture}[
      % Define block parameters (mostly shape)
      bloc/.style={
        rectangle, rounded corners,
        draw=black!30, very thick, inner sep=0,
      },
      invisible/.style={
        rectangle, draw=none,
        inner sep=0,
      },
      bloc1/.style={
        bloc,
        text width = \layerwidth/5*0.95,
        minimum width = \layerwidth/5,
        minimum height= 4*\layersep
      },
      bloc2/.style={
        bloc,
        text width = \layerwidth/5*0.95,
        minimum width=\layerwidth/5,
        minimum height=2*\layersep
      },
      bloc3/.style={
        bloc,
        text width=\layerwidth/2*0.95,
        minimum width=\layerwidth/2,
        minimum height=\layersep
      },
      invisible_bloc1/.style={
        invisible,
        text width=\layerwidth/5*0.95,
        minimum width=\layerwidth/5,
        minimum height=\layersep
      },
      invisible_bloc2/.style={
        invisible,
        text width=\layerwidth/5*0.95,
        minimum width=\layerwidth/5,
        minimum height=3*\layersep
      },
      title/.style={
        anchor=north west,
        color=black!50,
        font=\bfseries
      },
      subtitle/.style={
        anchor=north west,
        color=black!50,
        font=\bfseries
      },
    ]
    
    %%%%%%%%%%%%%%%%%%%%%%%%%
    %%%% DRAW THE CANVAS %%%%
    %%%%%%%%%%%%%%%%%%%%%%%%%

    % first the block, then the title
    
    % 1. KEY PARTNERS
    \node[bloc1] (b1) at (0*\layerwidth/10,4*\layersep) {};
    \node[title] at (b1.north west) {\underline{Key Partners}};
    
    \node[invisible_bloc2] (b11) at (0*\layerwidth/10,4.45*\layersep) {
      List your partners.
    };
    
    \node[invisible_bloc1] (b12) at (0*\layerwidth/10,2.5*\layersep) {
      Second text box if needed.
    };
    \node[title] at (b12.north west) {\underline{Something Else?}};

    % 4. KEY ACTIVITIES
    \node[bloc2] (b2) at (2*\layerwidth/10,5*\layersep) {
      What activities does your value proposition require?
    };
    \node[title] at (b2.north west) {\underline{Key Activities}};

    % 8. KEY RESOURCES
    \node[bloc2] (b3) at (2*\layerwidth/10,3*\layersep) {
      What resources does your value proposition require?
    };
    \node[title] at (b3.north west) {\underline{Key Resources}};

    % 7. COST STRUCTURE
    \node[bloc3] (b4) at (1.5*\layerwidth/10,1.5*\layersep) {
      List your fixed and variable costs.
    };
    \node[title] at (b4.north west) {\underline{Cost Structure}};

    % 6. REVENUE STREAMS
    \node[bloc3] (b5) at (6.5*\layerwidth/10,1.5*\layersep) {
      List your sources of revenue.
    };
    \node[title] at (b5.north west) {\underline{Revenue Streams}};

    % 7. ECO-SOCIAL COSTS
    \node[bloc3] (b6) at (1.5*\layerwidth/10,0.5*\layersep) {
      What ecological or social costs do you cause?
    };
    \node[title] at (b6.north west) {\underline{Eco-Social Costs}};

    % 6. ECO-SOCIAL BENEFITS
    \node[bloc3] (b7) at (6.5*\layerwidth/10,0.5*\layersep) {
      What ecological or social benefits do you generate?
    };
    \node[title] at (b7.north west) {\underline{Eco-Social Benefits}};

    % 3. VALUE PROPOSITIONS
    \node[bloc1] (b8) at (4*\layerwidth/10,4*\layersep) {};
    \node[title] at (b8.north west) {\underline{Value Propositions}};
    
    \node[invisible_bloc2] (b81) at (4*\layerwidth/10,4.45*\layersep) {
      Single, clear, compelling message that states why you are different and worth paying attention.
      What value do you deliver?
      What problems do you solve?
    };
    
    \node[invisible_bloc1] (b82) at (4*\layerwidth/10,2.5*\layersep) {
      List your X for Y analogy, e.g. YouTube = Flickr for videos.
    };
    \node[title] at (b82.north west) {\underline{High-Level Concept}};

    % 9. CUSTOMER RELATIONSHIP
    \node[bloc2] (b9) at (6*\layerwidth/10,5*\layersep) {
      What type of customer relationship will you maintain?
    };
    \node[title] at (b9.north west) {\underline{Customer Relationships}};

    % 5. CHANNELS
    \node[bloc2] (b10) at (6*\layerwidth/10,3*\layersep) {
      List your path to customers (inbound or outbound).
    };
    \node[title] at (b10.north west) {\underline{5. Channels}};


    % 2. CUSTOMER SEGMENTS
    \node[bloc1] (b11) at (8*\layerwidth/10,4*\layersep) {};
    \node[title] at (b11.north west) {\underline{Customer Segments}};
    
    \node[invisible_bloc2] (b111) at (8*\layerwidth/10,4.45*\layersep) {
      List your target customers and users.
    };
    
    \node[invisible_bloc1] (b112) at (8*\layerwidth/10,2.5*\layersep) {
      List the characteristics of your ideal customers.
    };
    \node[title] at (b112.north west) {\underline{Early Adopters}};

  \end{tikzpicture}
}

\end{document}