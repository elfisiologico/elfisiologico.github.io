#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const sourcePath = path.join(root, 'patients', 'explora-dolor', 'index.html');
const outputDir = path.join(root, 'profesionales', 'mapa-dolor-muscular');
const outputPath = path.join(outputDir, 'index.html');

let html = fs.readFileSync(sourcePath, 'utf8');

html = html
  .replace('<meta name="viewport" content="width=device-width,initial-scale=1">', '<meta name="viewport" content="width=device-width,initial-scale=1">\n  <base href="../../patients/explora-dolor/">')
  .replace('<title>Guía visual para entender dónde te duele · FisioLógico</title>', '<title>Mapa clínico de dolor muscular · FisioLógico</title>')
  .replace('content="Señala dónde te duele y compara mapas visuales sencillos para explicar mejor lo que notas. Guía educativa para pacientes de FisioLógico."', 'content="Mapa clínico por regiones, subzonas y patrones de dolor muscular referido para fisioterapeutas y profesionales sanitarios."')
  .replace('href="https://www.elfisiologico.com/patients/explora-dolor/"', 'href="https://www.elfisiologico.com/profesionales/mapa-dolor-muscular/"')
  .replace('content="Guía visual para entender dónde te duele · FisioLógico"', 'content="Mapa clínico de dolor muscular · FisioLógico"')
  .replace('content="Elige una zona del cuerpo y compara mapas sencillos para explicar mejor lo que sientes."', 'content="Explora regiones, subzonas y distribuciones de dolor muscular referido para apoyar la anamnesis y el razonamiento clínico."')
  .replace('content="https://www.elfisiologico.com/patients/explora-dolor/"', 'content="https://www.elfisiologico.com/profesionales/mapa-dolor-muscular/"')
  .replace(/<script type="application\/ld\+json">.*?<\/script>/, '<script type="application/ld+json">{"@context":"https://schema.org","@type":"MedicalWebPage","name":"Mapa clínico de dolor muscular","description":"Herramienta profesional para contrastar regiones, subzonas y patrones de dolor muscular referido.","url":"https://www.elfisiologico.com/profesionales/mapa-dolor-muscular/","dateModified":"2026-07-18","author":{"@id":"https://www.elfisiologico.com/sobre-fran/#person"},"audience":{"@type":"MedicalAudience","audienceType":"Fisioterapeutas y profesionales sanitarios"},"isPartOf":{"@id":"https://www.elfisiologico.com/#website"}}</script>')
  .replace('<body class="editorial-page pain-explorer-page" data-audience="patient">', '<body class="editorial-page pain-explorer-page professional-pain-map" data-audience="professional">')
  .replace('<a href="../../patients/" aria-current="page">Pacientes</a><a href="../../profesionales/">Profesionales</a>', '<a href="../../patients/">Pacientes</a><a href="../../profesionales/" aria-current="page">Profesionales</a>')
  .replace('<p class="section-label light">Guía visual para entender dónde te duele</p>', '<p class="section-label light">Herramienta visual para profesionales</p>')
  .replace('<h1>Señala dónde te duele. <br><em>Compara cómo se extiende.</em></h1>', '<h1>Mapa clínico del <br><em>dolor muscular.</em></h1>')
  .replace('<p class="hero-copy">Elige una zona del cuerpo y mira qué músculos pueden guardar relación con lo que sientes.</p>', '<p class="hero-copy">Explora regiones, subzonas y distribuciones para apoyar la anamnesis, la formulación de hipótesis y el razonamiento clínico.</p>')
  .replace('<span><b>1</b> Región</span><span><b>2</b> Zona</span><span><b>3</b> Mapas</span><span><b>4</b> Guía</span>', '<span><b>1</b> Región</span><span><b>2</b> Subzona</span><span><b>3</b> Patrón</span><span><b>4</b> Ficha</span>')
  .replace('<span>Te ayuda a</span>\n          <strong>Comparar dibujos y explicar mejor lo que notas</strong>\n          <span>No puede</span>\n          <strong>Decirte por sí sola cuál es la causa</strong>', '<span>Uso clínico</span>\n          <strong>Contrastar distribuciones y presentaciones clínicas</strong>\n          <span>Límite</span>\n          <strong>No sustituye exploración ni diagnóstico diferencial</strong>')
  .replace('<p class="section-label">Antes de explorar</p>\n          <h2 id="muscle-context-title">Entender tu dolor muscular empieza aquí</h2>', '<p class="section-label">Marco de uso</p>\n          <h2 id="muscle-context-title">Un mapa orienta una hipótesis; no la confirma</h2>')
  .replace('<p>Los músculos forman una parte importante de tu cuerpo y trabajan cada vez que te mueves o mantienes una postura. Cuando están más sensibles de lo habitual, el dolor puede sentirse en el propio músculo o aparecer en otra zona.</p>\n          <p>Esta guía te ayuda a señalar dónde te duele, comparar dibujos y explicar mejor lo que notas. <strong>Te orienta, pero no sustituye una valoración personal.</strong></p>', '<p>Esta herramienta conserva la presentación clínica, el patrón de dolor referido, los síntomas, los factores de activación y perpetuación y las acciones correctivas del corpus profesional.</p>\n          <p>Utiliza la concordancia visual como una pieza del razonamiento. <strong>Debe integrarse con anamnesis, exploración, carga, función, evolución y diagnóstico diferencial.</strong></p>')
  .replace('<div><p class="section-label">Antes de empezar</p><h2 id="safety-title">Primero, seguridad.</h2></div>', '<div><p class="section-label">Antes de interpretar</p><h2 id="safety-title">Cribado y seguridad.</h2></div>')
  .replace('<p>Pide ayuda urgente si notas presión fuerte en el pecho, dificultad para respirar, pérdida repentina de fuerza o sensibilidad, un golpe importante que no te deja moverte o cambios recientes al controlar la orina o las heces.</p>', '<p>Prioriza el cribado ante dolor torácico opresivo, disnea, déficit neurológico agudo, traumatismo relevante con pérdida funcional o alteraciones recientes de esfínteres.</p>')
  .replace('<li data-journey-step="3"><span>3</span><strong>Compara mapas</strong></li>', '<li data-journey-step="3"><span>3</span><strong>Compara patrones</strong></li>')
  .replaceAll('Mandíbula y oído', 'ATM y mandíbula')
  .replaceAll('Pecho y abdomen', 'Tórax y abdomen')
  .replaceAll('Parte media de la espalda', 'Dorsales')
  .replaceAll('Parte baja de la espalda', 'Lumbares')
  .replace('<span>Mapa corporal completo</span><strong>Elegir dónde me duele ↓</strong>', '<span>Mapa corporal completo</span><strong>Seleccionar región clínica ↓</strong>')
  .replace('<span>Si ya sabes qué buscar</span><strong>Buscar zona o músculo ↓</strong>', '<span>Acceso directo</span><strong>Buscar zona o músculo ↓</strong>')
  .replace('<div><p class="section-label">Paso 1 · todo el cuerpo</p><h2 id="whole-body-title">¿Dónde notas la molestia?</h2></div>', '<div><p class="section-label">Paso 1 · todo el cuerpo</p><h2 id="whole-body-title">Selecciona la región de interés</h2></div>')
  .replace('<p>Elige una región amplia. En el siguiente paso podrás señalar una zona más precisa.</p>', '<p>Selecciona una región amplia. En el siguiente paso podrás precisar la subzona clínica.</p>')
  .replace('<h2 id="visual-patterns-title" data-visual-patterns-title tabindex="-1">Mapas que pueden guardar relación</h2>', '<h2 id="visual-patterns-title" data-visual-patterns-title tabindex="-1">Patrones que pueden guardar relación</h2>')
  .replace('<span>Compara las zonas coloreadas con lo que notas. Los dibujos orientan, pero no están ordenados de más a menos probable.</span>', '<span>Contrasta la distribución coloreada con la anamnesis. Las coincidencias son orientativas y no están ordenadas por probabilidad.</span>')
  .replace('<div><strong>¿Ningún dibujo se parece?</strong><span>Cambia de zona o utiliza el buscador. Puede haber otras explicaciones que esta guía no muestra.</span></div>', '<div><strong>¿Ningún patrón presenta concordancia?</strong><span>Cambia de subzona o utiliza el buscador. La ausencia de coincidencia no descarta otras hipótesis.</span></div>')
  .replace('<div><p class="section-label">Todo el cuerpo</p><h2 id="corpus-title"><span data-corpus-total>66</span> guías para pacientes</h2></div>', '<div><p class="section-label">Corpus profesional</p><h2 id="corpus-title"><span data-corpus-total>66</span> fichas clínicas</h2></div>')
  .replace('<p>Busca la zona que te preocupa o el nombre de un músculo. Cada guía explica dónde podrías notarlo, qué puede empeorarlo y cuándo pedir ayuda.</p>', '<p>Busca una región o estructura. Cada ficha conserva presentación clínica, patrón referido, síntomas, perpetuación y acciones correctivas.</p>')
  .replace('<label>Parte del cuerpo', '<label>Región corporal')
  .replace('<div class="shell"><strong>Responsabilidad editorial</strong><span data-review-meta>Contenido de FisioLógico con revisión clínica profesional.</span><a href="../../profesionales/mapa-dolor-muscular/">Versión para profesionales sanitarios →</a></div>', '<div class="shell"><strong>Responsabilidad editorial</strong><span data-review-meta>Contenido de FisioLógico con revisión clínica profesional.</span><a href="../../patients/explora-dolor/">Versión en lenguaje sencillo para pacientes →</a></div>')
  .replace('<div><p>Una misma zona puede doler por motivos diferentes. Lo que ocurrió al empezar, las actividades que lo cambian y una valoración personal ayudan a entenderlo mejor.</p><a class="button button-primary" href="../../index.html#contacto">Consultar con FisioLógico</a></div>', '<div><p>La concordancia topográfica debe integrarse con el comportamiento de los síntomas, la función, los mecanismos plausibles y los hallazgos de la exploración.</p><a class="button button-primary" href="../../metodo-editorial/">Consultar el criterio editorial</a></div>')
  .replace('<footer class="site-footer"><div class="shell editorial-footer"><p>Información educativa para acompañar, no para sustituir una valoración individual.</p><a href="../">Volver a pacientes</a></div></footer>', '<footer class="site-footer"><div class="shell editorial-footer"><p>FisioLógico · evidencia, medida y razonamiento clínico.</p><a href="../../profesionales/">Volver al área profesional</a></div></footer>');

fs.mkdirSync(outputDir, { recursive: true });
fs.writeFileSync(outputPath, html, 'utf8');
console.log(`Mapa profesional generado: ${path.relative(root, outputPath)}`);
