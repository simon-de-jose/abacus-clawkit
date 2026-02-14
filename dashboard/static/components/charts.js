// Chart helper functions using ECharts

/**
 * Observe the chart container for size changes and auto-resize the ECharts instance.
 * Uses ResizeObserver so charts respond to CSS grid/flex reflows, not just window resize.
 */
function observeChartResize(chart, elementId) {
    const container = document.getElementById(elementId);
    if (!container) return;
    const ro = new ResizeObserver(() => {
        chart.resize();
    });
    ro.observe(container);
    // Also handle dispose to avoid leaks
    chart.on('disposed', () => ro.disconnect());
}

const CHART_COLORS = [
    '#E94560', '#4285F4', '#0F9D58', '#F4B400', '#9C27B0',
    '#FF6F00', '#00BCD4', '#8BC34A', '#FF5722', '#673AB7'
];

function createDonutChart(elementId, data, title) {
    // Phase 4: Use SVG renderer on mobile for better performance
    const isMobile = window.innerWidth < 768;
    const chart = echarts.init(document.getElementById(elementId), null, {
        renderer: isMobile ? 'svg' : 'canvas'
    });
    
    const option = {
        title: {
            text: title,
            left: 'center',
            textStyle: { fontSize: isMobile ? 14 : 16, fontWeight: 600, color: '#1A1A2E' }
        },
        tooltip: {
            trigger: 'item',
            formatter: '{b}: ${c} ({d}%)',
            // Phase 4: Larger tooltip trigger area on mobile
            triggerOn: isMobile ? 'click' : 'mousemove|click',
            padding: isMobile ? 12 : 10,
            textStyle: { fontSize: isMobile ? 13 : 12 }
        },
        grid: {
            bottom: 50
        },
        legend: {
            orient: 'horizontal',
            bottom: 5,
            left: 'center',
            padding: [5, 20],
            // Phase 4: Reduce legend density on mobile
            textStyle: { fontSize: isMobile ? 10 : 11 },
            itemGap: isMobile ? 10 : 15,
            type: isMobile ? 'scroll' : 'plain'
        },
        series: [{
            type: 'pie',
            radius: ['35%', '65%'],
            center: ['50%', '46%'],
            avoidLabelOverlap: true,
            itemStyle: {
                borderRadius: 8,
                borderColor: '#fff',
                borderWidth: 2
            },
            label: { show: false },
            labelLine: { show: false },
            emphasis: {
                label: {
                    show: !isMobile,
                    fontSize: 14,
                    fontWeight: 'bold'
                }
            },
            data: data.map((item, i) => ({
                name: item.name,
                value: item.value,
                itemStyle: { color: CHART_COLORS[i % CHART_COLORS.length] }
            }))
        }]
    };
    
    chart.setOption(option);
    observeChartResize(chart, elementId);
    return chart;
}

function createBarChart(elementId, categories, data, title) {
    const isMobile = window.innerWidth < 768;
    const chart = echarts.init(document.getElementById(elementId), null, {
        renderer: isMobile ? 'svg' : 'canvas'
    });
    
    const option = {
        title: {
            text: title,
            left: 'center',
            textStyle: { fontSize: isMobile ? 14 : 16, fontWeight: 600, color: '#1A1A2E' }
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: (params) => {
                return `${params[0].name}<br/>${params[0].marker} $${params[0].value.toFixed(2)}`;
            },
            triggerOn: isMobile ? 'click' : 'mousemove|click',
            padding: isMobile ? 12 : 10,
            textStyle: { fontSize: isMobile ? 13 : 12 }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: categories,
            // Phase 4: Reduce label density on mobile
            axisLabel: { 
                rotate: 45, 
                fontSize: isMobile ? 10 : 11,
                interval: isMobile ? 'auto' : 0
            }
        },
        yAxis: {
            type: 'value',
            axisLabel: { formatter: '${value}' }
        },
        series: [{
            data: data,
            type: 'bar',
            itemStyle: {
                color: '#E94560',
                borderRadius: [4, 4, 0, 0]
            },
            barWidth: '60%'
        }]
    };
    
    chart.setOption(option);
    observeChartResize(chart, elementId);
    return chart;
}

function createStackedBarChart(elementId, categories, series, title) {
    const isMobile = window.innerWidth < 768;
    const chart = echarts.init(document.getElementById(elementId), null, {
        renderer: isMobile ? 'svg' : 'canvas'
    });
    
    const option = {
        title: {
            text: title,
            left: 'center',
            textStyle: { fontSize: 16, fontWeight: 600, color: '#1A1A2E' }
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' }
        },
        legend: {
            top: 30,
            textStyle: { fontSize: 12 }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: categories
        },
        yAxis: {
            type: 'value',
            axisLabel: { formatter: '${value}' }
        },
        series: series.map((s, i) => ({
            name: s.name,
            type: 'bar',
            stack: 'total',
            data: s.data,
            itemStyle: { color: CHART_COLORS[i % CHART_COLORS.length] }
        }))
    };
    
    chart.setOption(option);
    observeChartResize(chart, elementId);
    return chart;
}

function createLineChart(elementId, categories, series, title) {
    const isMobile = window.innerWidth < 768;
    const chart = echarts.init(document.getElementById(elementId), null, {
        renderer: isMobile ? 'svg' : 'canvas'
    });
    
    const option = {
        title: {
            text: title,
            left: 'center',
            textStyle: { fontSize: 16, fontWeight: 600, color: '#1A1A2E' }
        },
        tooltip: {
            trigger: 'axis'
        },
        legend: {
            top: 30,
            textStyle: { fontSize: 12 }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: categories,
            boundaryGap: false
        },
        yAxis: {
            type: 'value',
            axisLabel: { formatter: '${value}' }
        },
        series: series.map((s, i) => ({
            name: s.name,
            type: 'line',
            smooth: true,
            data: s.data,
            itemStyle: { color: CHART_COLORS[i % CHART_COLORS.length] }
        }))
    };
    
    chart.setOption(option);
    observeChartResize(chart, elementId);
    return chart;
}

function createSankeyChart(elementId, nodes, links, title) {
    const isMobile = window.innerWidth < 768;
    const chart = echarts.init(document.getElementById(elementId), null, {
        renderer: isMobile ? 'svg' : 'canvas'
    });
    
    const option = {
        title: {
            text: title,
            left: 'center',
            textStyle: { fontSize: 16, fontWeight: 600, color: '#1A1A2E' }
        },
        tooltip: {
            trigger: 'item',
            formatter: (params) => {
                if (params.dataType === 'edge') {
                    return `${params.data.source} → ${params.data.target}<br/>$${params.data.value.toFixed(2)}`;
                } else {
                    return params.name;
                }
            }
        },
        series: [{
            type: 'sankey',
            layout: 'none',
            emphasis: { focus: 'adjacency' },
            data: nodes,
            links: links,
            lineStyle: {
                color: 'gradient',
                curveness: 0.5
            },
            itemStyle: {
                borderWidth: 1,
                borderColor: '#fff'
            },
            label: {
                fontSize: 12
            }
        }]
    };
    
    chart.setOption(option);
    observeChartResize(chart, elementId);
    return chart;
}

function createHorizontalBarChart(elementId, categories, data, title) {
    const isMobile = window.innerWidth < 768;
    const chart = echarts.init(document.getElementById(elementId), null, {
        renderer: isMobile ? 'svg' : 'canvas'
    });
    
    const option = {
        title: {
            text: title,
            left: 'center',
            textStyle: { fontSize: 16, fontWeight: 600, color: '#1A1A2E' }
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: (params) => {
                return `${params[0].name}<br/>${params[0].marker} $${params[0].value.toFixed(2)}`;
            }
        },
        grid: {
            left: '15%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'value',
            axisLabel: { formatter: '${value}' }
        },
        yAxis: {
            type: 'category',
            data: categories
        },
        series: [{
            data: data,
            type: 'bar',
            itemStyle: {
                color: '#4285F4',
                borderRadius: [0, 4, 4, 0]
            },
            barWidth: '60%'
        }]
    };
    
    chart.setOption(option);
    observeChartResize(chart, elementId);
    return chart;
}

function createStackedAreaChart(elementId, categories, series, title) {
    const isMobile = window.innerWidth < 768;
    const chart = echarts.init(document.getElementById(elementId), null, {
        renderer: isMobile ? 'svg' : 'canvas'
    });
    
    const option = {
        title: {
            text: title,
            left: 'center',
            textStyle: { fontSize: 16, fontWeight: 600, color: '#1A1A2E' }
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'cross' }
        },
        legend: {
            top: 30,
            textStyle: { fontSize: 12 }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: categories,
            boundaryGap: false
        },
        yAxis: {
            type: 'value',
            axisLabel: { formatter: '${value}' }
        },
        series: series.map((s, i) => ({
            name: s.name,
            type: 'line',
            stack: 'total',
            areaStyle: { opacity: 0.7 },
            emphasis: { focus: 'series' },
            smooth: true,
            data: s.data,
            itemStyle: { color: CHART_COLORS[i % CHART_COLORS.length] }
        }))
    };
    
    chart.setOption(option);
    observeChartResize(chart, elementId);
    return chart;
}

function createDonutWithCenterLabel(elementId, data, centerLabel, title) {
    const isMobile = window.innerWidth < 768;
    const chart = echarts.init(document.getElementById(elementId), null, {
        renderer: isMobile ? 'svg' : 'canvas'
    });
    
    const option = {
        title: {
            text: title,
            left: 'center',
            top: 10,
            textStyle: { fontSize: 16, fontWeight: 600, color: '#1A1A2E' }
        },
        tooltip: {
            trigger: 'item',
            formatter: '{b}: ${c} ({d}%)'
        },
        graphic: {
            type: 'text',
            left: 'center',
            top: 'center',
            style: {
                text: centerLabel,
                textAlign: 'center',
                fill: '#1A1A2E',
                fontSize: 24,
                fontWeight: 700
            }
        },
        series: [{
            type: 'pie',
            radius: ['45%', '70%'],
            center: ['50%', '55%'],
            avoidLabelOverlap: false,
            itemStyle: {
                borderRadius: 8,
                borderColor: '#fff',
                borderWidth: 2
            },
            label: { show: false },
            labelLine: { show: false },
            emphasis: {
                label: {
                    show: !isMobile,
                    fontSize: 14,
                    fontWeight: 'bold'
                }
            },
            data: data.map((item, i) => ({
                name: item.name,
                value: item.value,
                itemStyle: { color: CHART_COLORS[i % CHART_COLORS.length] }
            }))
        }]
    };
    
    chart.setOption(option);
    observeChartResize(chart, elementId);
    return chart;
}
