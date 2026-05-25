(function () {
    const TIPOS_SELECCION = ['seleccion_unica', 'seleccion_multiple'];
    const TIPOS_CON_OPCIONES = ['seleccion_unica', 'seleccion_multiple', 'matriz_seleccion'];
    const TIPO_MATRIZ = 'matriz_seleccion';
    const TIPO_TEXTO_CORTO = 'texto_corto';
    const PREFIJO_OPCIONES = 'opciones';
    const PREFIJO_FILAS = 'filas_matriz';

    const tipoSelect = document.getElementById('id_tipo');
    const opcionesBlock = document.getElementById('opciones-block');
    const opcionesBlockTitle = document.getElementById('opciones-block-title');
    const opcionesBlockHelp = document.getElementById('opciones-block-help');
    const filasMatrizBlock = document.getElementById('filas-matriz-block');
    const textoMaximoField = document.getElementById('field-texto-maximo');
    const btnAgregarOpcion = document.getElementById('btn-agregar-opcion');
    const btnAgregarFila = document.getElementById('btn-agregar-fila');
    const btnAplicarPlantilla = document.getElementById('btn-aplicar-plantilla');
    const selectPlantilla = document.getElementById('id-plantilla-opciones');
    const opcionesContainer = document.getElementById('opciones-forms');
    const filasContainer = document.getElementById('filas-matriz-forms');
    const templateOpcion = document.getElementById('opcion-empty-template');
    const templateFila = document.getElementById('fila-empty-template');
    const totalOpcionesInput = document.getElementById('id_opciones-TOTAL_FORMS');
    const totalFilasInput = document.getElementById('id_filas_matriz-TOTAL_FORMS');
    const plantillasDataEl = document.getElementById('opciones-plantillas-data');
    const preguntaForm = document.getElementById('encuesta-pregunta-form');

    const plantillasPorId = {};

    function cargarPlantillas() {
        if (!plantillasDataEl) {
            return;
        }
        try {
            const plantillas = JSON.parse(plantillasDataEl.textContent);
            plantillas.forEach(function (plantilla) {
                plantillasPorId[plantilla.id] = plantilla.opciones;
            });
        } catch (e) {
            console.error('No se pudieron cargar las plantillas de opciones.', e);
        }
    }

    cargarPlantillas();

    function enlazarAutocompletado(input) {
        if (!input || input.dataset.sugerenciasEnlazadas === '1') {
            return;
        }
        input.setAttribute('list', 'opciones-sugerencias');
        input.setAttribute('autocomplete', 'off');
        input.dataset.sugerenciasEnlazadas = '1';
    }

    function obtenerSiguienteIndice(container, prefijo) {
        let maxIndex = -1;
        if (!container) {
            return 0;
        }
        const regex = new RegExp('^' + prefijo + '-(\\d+)-');
        container.querySelectorAll('input[name]').forEach(function (input) {
            const match = input.name.match(regex);
            if (match) {
                maxIndex = Math.max(maxIndex, parseInt(match[1], 10));
            }
        });
        return maxIndex + 1;
    }

    function actualizarTotalForms(container, totalInput, prefijo) {
        if (!totalInput || !container) {
            return;
        }
        let maxIndex = -1;
        const regex = new RegExp('^' + prefijo + '-(\\d+)-');
        container.querySelectorAll('input[name]').forEach(function (input) {
            const match = input.name.match(regex);
            if (match) {
                maxIndex = Math.max(maxIndex, parseInt(match[1], 10));
            }
        });
        totalInput.value = maxIndex + 1;
    }

    function reindexarFila(row, index, prefijo) {
        row.querySelectorAll('input[name]').forEach(function (input) {
            input.name = input.name.replace(
                new RegExp('^' + prefijo + '-\\d+-'),
                prefijo + '-' + index + '-'
            );
            if (input.id) {
                input.id = input.id.replace(
                    new RegExp('^id_' + prefijo + '-\\d+-'),
                    'id_' + prefijo + '-' + index + '-'
                );
            }
        });
    }

    function agregarFilaForm(prefijo, container, template, totalInput, valorInicial, inputSelector) {
        if (!template || !container || !totalInput) {
            return null;
        }
        const index = obtenerSiguienteIndice(container, prefijo);
        const html = template.innerHTML.replace(/__prefix__/g, String(index));
        const wrapper = document.createElement('div');
        wrapper.innerHTML = html.trim();
        const row = wrapper.firstElementChild;
        container.appendChild(row);
        actualizarTotalForms(container, totalInput, prefijo);

        const input = row.querySelector(inputSelector);
        if (prefijo === PREFIJO_OPCIONES) {
            enlazarAutocompletado(input);
        }
        if (valorInicial && input) {
            input.value = valorInicial;
        }
        return row;
    }

    function agregarOpcion(valorInicial) {
        return agregarFilaForm(
            PREFIJO_OPCIONES,
            opcionesContainer,
            templateOpcion,
            totalOpcionesInput,
            valorInicial,
            'input[name$="-texto"]'
        );
    }

    function agregarFila(valorInicial) {
        return agregarFilaForm(
            PREFIJO_FILAS,
            filasContainer,
            templateFila,
            totalFilasInput,
            valorInicial,
            'input[name$="-texto"]'
        );
    }

    function filaTieneContenido(row) {
        const textoInput = row.querySelector('input[name$="-texto"]');
        const idInput = row.querySelector('input[name$="-id"]');
        const texto = textoInput ? textoInput.value.trim() : '';
        const tieneId = idInput && idInput.value;
        return Boolean(texto || tieneId);
    }

    function limpiarFilasParaPlantilla(container, totalInput, prefijo) {
        if (!container) {
            return;
        }
        container.querySelectorAll('.encuesta-opcion-row').forEach(function (row) {
            const idInput = row.querySelector('input[name$="-id"]');
            const deleteInput = row.querySelector('input[name$="-DELETE"]');
            if (idInput && idInput.value) {
                if (deleteInput) {
                    deleteInput.checked = true;
                }
                row.classList.add('encuesta-opcion-row--deleted');
                row.style.display = 'none';
            } else {
                row.remove();
            }
        });
        actualizarTotalForms(container, totalInput, prefijo);
    }

    function normalizarFormset(container, totalInput, prefijo) {
        if (!container || !totalInput) {
            return;
        }
        const filas = [];
        container.querySelectorAll('.encuesta-opcion-row').forEach(function (row) {
            const deleteInput = row.querySelector('input[name$="-DELETE"]');
            const idInput = row.querySelector('input[name$="-id"]');
            const textoInput = row.querySelector('input[name$="-texto"]');
            const tieneId = idInput && idInput.value;

            if (!tieneId && deleteInput && deleteInput.checked) {
                row.remove();
                return;
            }
            if (!tieneId && (!textoInput || !textoInput.value.trim())) {
                row.remove();
                return;
            }
            filas.push(row);
        });

        filas.forEach(function (row, index) {
            reindexarFila(row, index, prefijo);
        });
        totalInput.value = filas.length;
    }

    function toggleBlocks() {
        if (!tipoSelect) {
            return;
        }
        const tipo = tipoSelect.value;
        const usaOpciones = TIPOS_CON_OPCIONES.includes(tipo);
        const esMatriz = tipo === TIPO_MATRIZ;
        const esTextoCorto = tipo === TIPO_TEXTO_CORTO;

        if (opcionesBlock) {
            opcionesBlock.classList.toggle('is-hidden', !usaOpciones);
        }
        if (filasMatrizBlock) {
            filasMatrizBlock.classList.toggle('is-hidden', !esMatriz);
        }
        if (textoMaximoField) {
            textoMaximoField.classList.toggle('is-hidden', !esTextoCorto);
        }
        if (opcionesBlockTitle) {
            opcionesBlockTitle.textContent = esMatriz
                ? 'Columnas de la escala'
                : 'Opciones de respuesta';
        }
        if (opcionesBlockHelp) {
            opcionesBlockHelp.textContent = esMatriz
                ? 'Defina al menos dos columnas (etiquetas de la escala). Puede aplicar una plantilla.'
                : 'Ingrese al menos dos opciones. Puede escribir y elegir sugerencias frecuentes o aplicar una plantilla completa.';
        }
        if (btnAgregarOpcion) {
            btnAgregarOpcion.textContent = esMatriz ? 'Agregar columna' : 'Agregar opción';
        }
    }

    function aplicarPlantilla(event) {
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }

        if (!selectPlantilla || !tipoSelect) {
            return;
        }

        const tipo = tipoSelect.value;
        if (!TIPOS_CON_OPCIONES.includes(tipo)) {
            window.alert(
                'Seleccione un tipo con opciones (lista o matriz de selección).'
            );
            return;
        }

        const plantillaId = selectPlantilla.value;
        const opciones = plantillasPorId[plantillaId];
        if (!opciones || !opciones.length) {
            window.alert('Seleccione una plantilla de la lista.');
            return;
        }

        const filasVisibles = opcionesContainer
            ? opcionesContainer.querySelectorAll(
                  '.encuesta-opcion-row:not(.encuesta-opcion-row--deleted)'
              )
            : [];
        const tieneContenido = Array.from(filasVisibles).some(filaTieneContenido);

        if (
            tieneContenido &&
            !window.confirm(
                '¿Reemplazar las columnas actuales por las de la plantilla seleccionada?'
            )
        ) {
            return;
        }

        limpiarFilasParaPlantilla(opcionesContainer, totalOpcionesInput, PREFIJO_OPCIONES);
        opciones.forEach(function (texto) {
            agregarOpcion(texto);
        });
    }

    function normalizarFormsetAntesDeEnviar() {
        if (!tipoSelect) {
            return;
        }
        const tipo = tipoSelect.value;
        if (TIPOS_CON_OPCIONES.includes(tipo)) {
            normalizarFormset(opcionesContainer, totalOpcionesInput, PREFIJO_OPCIONES);
        }
        if (tipo === TIPO_MATRIZ) {
            normalizarFormset(filasContainer, totalFilasInput, PREFIJO_FILAS);
        }
    }

    if (tipoSelect) {
        tipoSelect.addEventListener('change', toggleBlocks);
        toggleBlocks();
    }

    if (btnAgregarOpcion) {
        btnAgregarOpcion.addEventListener('click', function (event) {
            event.preventDefault();
            agregarOpcion();
        });
    }

    if (btnAgregarFila) {
        btnAgregarFila.addEventListener('click', function (event) {
            event.preventDefault();
            agregarFila();
        });
    }

    if (btnAplicarPlantilla) {
        btnAplicarPlantilla.addEventListener('click', aplicarPlantilla);
    }

    if (preguntaForm) {
        preguntaForm.addEventListener('submit', normalizarFormsetAntesDeEnviar);
    }

    if (opcionesContainer) {
        opcionesContainer.querySelectorAll('input[name$="-texto"]').forEach(enlazarAutocompletado);
    }
})();
