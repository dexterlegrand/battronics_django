
function capacityPlot(graph, x, cap_ch, cap_dis, xlabel) {
    var data = [{
        x: x,
        y: cap_ch,
        type: 'scatter',
        mode: 'markers',
        name: 'Charge capacity',
        marker: {size: 12}
    },
        {
            x: x,
            y: cap_dis,
            type: 'scatter',
            mode: 'markers',
            name: 'Discharge capacity',
            marker: {size: 12}
        },];

    var layout = {
        xaxis: {
            title: xlabel
        },
        yaxis: {
            title: 'Capacity (Ah)'
        },
        height: 400
    }

    Plotly.newPlot(graph, data, layout);
}

function updatePredictions(graph, x, prediction, eol) {
    Plotly.addTraces(graph, {
        x: x,
        y: prediction,
        name: 'Prediction'
    });
        Plotly.addTraces(graph, {
        x: x,
        y: eol,
        name: 'End of life',
        mode: 'lines',
        line: {
            dash: 'dash',
            width: 2,
            color: 'black'},

      });
}

// TODO: Match x-axis with with capacity plot
function residualPlot(graph, x, residuals, baseline, xlabel) {
    var data = [{
        x: x,
        y: residuals,
        type: 'scatter',
        mode: 'markers',
        name: 'Residual',
        marker: {
            size: 12,
            color: 'darkorange'}
    },
        {
            x: x,
            y: baseline,
            name: 'Zero line',
            mode: 'lines',
            line: {
                dash: 'dash',
                width: 2,
                color: 'black'},
        },];

    var layout = {
        xaxis: {
            title: xlabel
        },
        yaxis: {
            title: 'Capacity residual (Ah)'
        },
        height: 400
    }

    Plotly.newPlot(graph, data, layout);
}