import { createTheme } from '@mantine/core';

// Desktop-first: kompakte Defaults (dichte Tabellen, kleine Inputs), aber über
// die Mantine-Größen weiterhin touch-tauglich. Primärfarbe Teal wie bisher.
export const theme = createTheme({
  primaryColor: 'teal',
  defaultRadius: 'sm',
  fontFamily: 'Roboto, system-ui, -apple-system, sans-serif',
  headings: { fontFamily: 'Roboto, system-ui, sans-serif' },
  components: {
    Table: {
      defaultProps: {
        striped: true,
        highlightOnHover: true,
        withTableBorder: true,
        withColumnBorders: false,
        verticalSpacing: 'xs',
        horizontalSpacing: 'sm',
      },
    },
    Card: { defaultProps: { withBorder: true, radius: 'sm', padding: 'md' } },
    Paper: { defaultProps: { withBorder: true, radius: 'sm' } },
    Button: { defaultProps: { size: 'sm' } },
    TextInput: { defaultProps: { size: 'sm' } },
    PasswordInput: { defaultProps: { size: 'sm' } },
    NumberInput: { defaultProps: { size: 'sm' } },
    Select: { defaultProps: { size: 'sm' } },
  },
});
