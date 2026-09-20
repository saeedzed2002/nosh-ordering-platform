import type { Preview } from "@storybook/react-vite";

import "../src/styles.css";

const preview = {
  parameters: {
    a11y: {
      test: "error",
    },
    controls: {
      expanded: true,
    },
  },
} satisfies Preview;

export default preview;
