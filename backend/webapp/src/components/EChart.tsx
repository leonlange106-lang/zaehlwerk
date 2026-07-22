import ReactECharts from 'echarts-for-react';
import { useComputedColorScheme } from '@mantine/core';
import type { EChartsOption } from 'echarts';

// Dünner Wrapper um ECharts, der Light/Dark aus dem Mantine-Farbschema
// übernimmt (transparenter Hintergrund, passende Textfarbe) und eine
// einheitliche Höhe/Reaktivität liefert.
export function EChart({ option, height = 280 }: { option: EChartsOption; height?: number }) {
  const scheme = useComputedColorScheme('light');
  const dark = scheme === 'dark';
  const merged: EChartsOption = {
    backgroundColor: 'transparent',
    textStyle: { color: dark ? '#C1C2C5' : '#1A1B1E' },
    ...option,
  };
  return (
    <ReactECharts
      option={merged}
      style={{ height, width: '100%' }}
      opts={{ renderer: 'canvas' }}
      notMerge
      lazyUpdate
    />
  );
}
