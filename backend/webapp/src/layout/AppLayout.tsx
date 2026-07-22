import { AppShell, Burger, Group, ScrollArea, NavLink, ActionIcon, Title, Menu, Text, useMantineColorScheme } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import {
  IconGauge, IconClipboardList, IconReceipt2, IconChartHistogram, IconHistory,
  IconSettings, IconShieldLock, IconSun, IconMoon, IconLogout, IconUser,
} from '@tabler/icons-react';
import { NavLink as RouterLink, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

interface NavItem {
  to: string;
  label: string;
  icon: typeof IconGauge;
  adminOnly?: boolean;
}

const NAV: NavItem[] = [
  { to: '/',         label: 'Dashboard',     icon: IconGauge },
  { to: '/readings', label: 'Zählerstände',  icon: IconClipboardList },
  { to: '/tariffs',  label: 'Tarife',        icon: IconReceipt2 },
  { to: '/reports',  label: 'Auswertungen',  icon: IconChartHistogram },
  { to: '/audit',    label: 'Audit-Log',     icon: IconHistory, adminOnly: true },
  { to: '/settings', label: 'Einstellungen', icon: IconSettings },
  { to: '/admin',    label: 'Admin',         icon: IconShieldLock, adminOnly: true },
];

export function AppLayout() {
  const [opened, { toggle, close }] = useDisclosure(false);
  const { colorScheme, toggleColorScheme } = useMantineColorScheme();
  const { pathname } = useLocation();
  const { user, isAdmin, logout } = useAuth();

  return (
    <AppShell
      header={{ height: 54 }}
      navbar={{ width: 240, breakpoint: 'sm', collapsed: { mobile: !opened } }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between" wrap="nowrap">
          <Group gap="sm" wrap="nowrap">
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
            <Title order={4}>Zählwerk</Title>
          </Group>
          <Group gap="xs" wrap="nowrap">
            <ActionIcon variant="default" onClick={toggleColorScheme} aria-label="Design umschalten">
              {colorScheme === 'dark' ? <IconSun size={18} /> : <IconMoon size={18} />}
            </ActionIcon>
            <Menu position="bottom-end" withArrow>
              <Menu.Target>
                <ActionIcon variant="default" aria-label="Konto"><IconUser size={18} /></ActionIcon>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Label>
                  <Text size="sm" fw={600}>{user?.display_name ?? 'Konto'}</Text>
                  <Text size="xs" c="dimmed">{user?.role}</Text>
                </Menu.Label>
                <Menu.Divider />
                <Menu.Item leftSection={<IconLogout size={16} />} onClick={() => void logout()}>
                  Abmelden
                </Menu.Item>
              </Menu.Dropdown>
            </Menu>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="xs">
        <AppShell.Section grow component={ScrollArea}>
          {NAV.filter((i) => !i.adminOnly || isAdmin).map((i) => {
            const Icon = i.icon;
            return (
              <NavLink
                key={i.to}
                component={RouterLink}
                to={i.to}
                label={i.label}
                leftSection={<Icon size={18} stroke={1.6} />}
                active={i.to === '/' ? pathname === '/' : pathname.startsWith(i.to)}
                onClick={close}
              />
            );
          })}
        </AppShell.Section>
      </AppShell.Navbar>

      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
