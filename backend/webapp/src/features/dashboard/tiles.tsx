import { Card, Group, Text, Badge, Stack, ThemeIcon } from '@mantine/core';
import { IconTrendingUp, IconTrendingDown, IconMinus } from '@tabler/icons-react';
import type { EChartsOption } from 'echarts';
import dayjs from 'dayjs';
import type { DashboardData, DashboardSystem, DashboardTile, SeriesPoint, Timeframe } from '../../api/types';
import { EChart } from '../../components/EChart';
import { fmtValue, fmtCost, fmtDate, fmtNumber } from '../../util/format';

export const TILE_LABELS: Record<DashboardTile['type'], string> = {
  latest_reading: 'Aktueller Stand',
  line_chart: 'Verlaufsdiagramm',
  pie_chart: 'Kostenverteilung',
  cost_summary: 'Kostenübersicht',
  trend: 'Trend',
  cost_forecast: 'Kostenprognose',
};

export const TIMEFRAME_LABELS: Record<Timeframe, string> = {
  '7d': '7 Tage', '30d': '30 Tage', '90d': '90 Tage', ytd: 'Lfd. Jahr',
  '12m': '12 Monate', all: 'Gesamt', custom: 'Zeitraum',
};

// Serie nach Zeitfenster einer Kachel beschneiden.
export function filterSeries(series: SeriesPoint[], tile: DashboardTile): SeriesPoint[] {
  const tf = tile.timeframe ?? '12m';
  if (tf === 'all' || series.length === 0) return series;
  let from: dayjs.Dayjs | null = null;
  let to: dayjs.Dayjs | null = null;
  const now = dayjs();
  switch (tf) {
    case '7d': from = now.subtract(7, 'day'); break;
    case '30d': from = now.subtract(30, 'day'); break;
    case '90d': from = now.subtract(90, 'day'); break;
    case 'ytd': from = now.startOf('year'); break;
    case '12m': from = now.subtract(12, 'month'); break;
    case 'custom':
      from = tile.range_from ? dayjs(tile.range_from) : null;
      to = tile.range_to ? dayjs(tile.range_to) : null;
      break;
  }
  return series.filter((p) => {
    const d = dayjs(p.d);
    if (from && d.isBefore(from)) return false;
    if (to && d.isAfter(to)) return false;
    return true;
  });
}

function tileSystems(tile: DashboardTile, systems: DashboardSystem[]): DashboardSystem[] {
  const ids = (tile.system_ids && tile.system_ids.length ? tile.system_ids
    : tile.system_id ? [tile.system_id] : []);
  if (!ids.length) return [];
  const map = new Map(systems.map((s) => [s.id, s]));
  return ids.map((id) => map.get(id)).filter((s): s is DashboardSystem => !!s);
}

export function TileBody({ tile, data }: { tile: DashboardTile; data: DashboardData }) {
  const systems = data.systems;
  switch (tile.type) {
    case 'latest_reading': return <LatestReadingTile tile={tile} systems={systems} />;
    case 'line_chart': return <LineChartTile tile={tile} systems={systems} />;
    case 'pie_chart': return <PieChartTile tile={tile} systems={systems} />;
    case 'cost_summary': return <CostSummaryTile tile={tile} systems={systems} />;
    case 'trend': return <TrendTile tile={tile} systems={systems} />;
    case 'cost_forecast': return <CostForecastTile tile={tile} systems={systems} />;
    default: return <Text c="dimmed" size="sm">Unbekannter Kacheltyp</Text>;
  }
}

function Empty({ hint }: { hint: string }) {
  return <Text c="dimmed" size="sm">{hint}</Text>;
}

function LatestReadingTile({ tile, systems }: { tile: DashboardTile; systems: DashboardSystem[] }) {
  const s = tileSystems(tile, systems)[0];
  if (!s) return <Empty hint="Kein System zugeordnet" />;
  return (
    <Stack gap={2}>
      <Group gap={8}>
        <span style={{ width: 10, height: 10, borderRadius: 5, background: s.farbe, display: 'inline-block' }} />
        <Text size="sm" fw={600}>{s.name}</Text>
      </Group>
      <Text fz={28} fw={700} lh={1.1}>{fmtValue(s.latest, s.einheit)}</Text>
      <Text size="xs" c="dimmed">Stand {fmtDate(s.latest_datum)} · Ø {fmtValue(s.avg_per_day, s.einheit)}/Tag</Text>
    </Stack>
  );
}

function LineChartTile({ tile, systems }: { tile: DashboardTile; systems: DashboardSystem[] }) {
  const chosen = tileSystems(tile, systems);
  const list = chosen.length ? chosen : systems.slice(0, 1);
  if (!list.length) return <Empty hint="Keine Daten" />;
  const first = filterSeries(list[0].series, tile);
  const option: EChartsOption = {
    grid: { top: 16, right: 10, bottom: 24, left: 44 },
    tooltip: { trigger: 'axis' },
    legend: list.length > 1 ? { top: 0, type: 'scroll' } : undefined,
    xAxis: { type: 'category', data: first.map((p) => p.d), show: first.length > 0 },
    yAxis: { type: 'value' },
    series: list.map((s) => ({
      name: s.name, type: 'line', smooth: true, showSymbol: false,
      data: filterSeries(s.series, tile).map((p) => p.v),
      lineStyle: { width: 2, color: s.farbe }, itemStyle: { color: s.farbe },
      areaStyle: list.length === 1 ? { opacity: 0.12 } : undefined,
    })),
  };
  return <EChart option={option} height={200} />;
}

function PieChartTile({ tile, systems }: { tile: DashboardTile; systems: DashboardSystem[] }) {
  const chosen = tileSystems(tile, systems);
  const list = (chosen.length ? chosen : systems).filter((s) => (s.total_cost_tariff ?? s.total_cost ?? 0) > 0);
  if (!list.length) return <Empty hint="Keine Kostendaten" />;
  const option: EChartsOption = {
    tooltip: { trigger: 'item', formatter: '{b}: {c} € ({d}%)' },
    series: [{
      type: 'pie', radius: ['40%', '70%'], avoidLabelOverlap: true,
      itemStyle: { borderRadius: 4, borderColor: 'var(--mantine-color-body)', borderWidth: 2 },
      label: { fontSize: 11 },
      data: list.map((s) => ({
        name: s.name, value: Number((s.total_cost_tariff ?? s.total_cost ?? 0).toFixed(2)),
        itemStyle: { color: s.farbe },
      })),
    }],
  };
  return <EChart option={option} height={200} />;
}

function CostSummaryTile({ tile, systems }: { tile: DashboardTile; systems: DashboardSystem[] }) {
  const list = (() => { const c = tileSystems(tile, systems); return c.length ? c : systems; })();
  const total = list.reduce((sum, s) => sum + (s.total_cost_tariff ?? s.total_cost ?? 0), 0);
  return (
    <Stack gap={6}>
      <Text size="xs" c="dimmed">Gesamtkosten</Text>
      <Text fz={28} fw={700} lh={1.1}>{fmtCost(total)}</Text>
      <Stack gap={2}>
        {list.slice(0, 5).map((s) => (
          <Group key={s.id} justify="space-between" gap="xs">
            <Group gap={6}>
              <span style={{ width: 8, height: 8, borderRadius: 4, background: s.farbe, display: 'inline-block' }} />
              <Text size="xs">{s.name}</Text>
            </Group>
            <Text size="xs" c="dimmed">{fmtCost(s.total_cost_tariff ?? s.total_cost)}</Text>
          </Group>
        ))}
      </Stack>
    </Stack>
  );
}

function TrendTile({ tile, systems }: { tile: DashboardTile; systems: DashboardSystem[] }) {
  const s = tileSystems(tile, systems)[0];
  if (!s) return <Empty hint="Kein System zugeordnet" />;
  const series = filterSeries(s.series, tile);
  const first = series.find((p) => p.v != null)?.v ?? null;
  const last = [...series].reverse().find((p) => p.v != null)?.v ?? null;
  const delta = first != null && last != null && first !== 0 ? ((last - first) / Math.abs(first)) * 100 : null;
  const dir = delta == null ? 'flat' : delta > 1 ? 'up' : delta < -1 ? 'down' : 'flat';
  const color = dir === 'up' ? 'orange' : dir === 'down' ? 'teal' : 'gray';
  const Icon = dir === 'up' ? IconTrendingUp : dir === 'down' ? IconTrendingDown : IconMinus;
  const option: EChartsOption = {
    grid: { top: 6, right: 4, bottom: 4, left: 4 },
    xAxis: { type: 'category', show: false, data: series.map((p) => p.d) },
    yAxis: { type: 'value', show: false },
    tooltip: { trigger: 'axis' },
    series: [{
      type: 'line', smooth: true, showSymbol: false, data: series.map((p) => p.v),
      lineStyle: { width: 2, color: s.farbe }, itemStyle: { color: s.farbe }, areaStyle: { opacity: 0.12 },
    }],
  };
  return (
    <Stack gap={4}>
      <Group gap={8}>
        <ThemeIcon size="sm" variant="light" color={color}><Icon size={14} /></ThemeIcon>
        <Text size="sm" fw={600}>{s.name}</Text>
        {delta != null && <Badge size="sm" variant="light" color={color}>{delta > 0 ? '+' : ''}{fmtNumber(delta)} %</Badge>}
      </Group>
      {series.length > 1 && <EChart option={option} height={90} />}
    </Stack>
  );
}

function CostForecastTile({ tile, systems }: { tile: DashboardTile; systems: DashboardSystem[] }) {
  const s = tileSystems(tile, systems)[0] ?? systems[0];
  if (!s) return <Empty hint="Keine Daten" />;
  const p = s.prognosis;
  if (!p) return <Empty hint="Keine Prognose verfügbar" />;
  const exceeds = p.exceeds_abschlag ?? false;
  return (
    <Stack gap={4}>
      <Text size="sm" fw={600}>{s.name}</Text>
      <Text fz={24} fw={700} lh={1.1}>{fmtCost(p.projected_cost)}</Text>
      <Text size="xs" c="dimmed">Hochrechnung · {fmtValue(p.projected_consumption, s.einheit)}</Text>
      {p.abschlag_annual != null && (
        <Badge variant="light" color={exceeds ? 'orange' : 'teal'}>
          {exceeds ? 'über' : 'im'} Abschlag ({fmtCost(p.abschlag_annual)})
        </Badge>
      )}
    </Stack>
  );
}

export function TileCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card h="100%" withBorder>
      {title && <Text size="xs" c="dimmed" tt="uppercase" fw={600} mb={6}>{title}</Text>}
      {children}
    </Card>
  );
}
