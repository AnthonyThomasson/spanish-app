import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.anthonythomasson.paso',
  appName: 'Paso',
  webDir: 'dist',
  server: {
    androidScheme: 'https',
  },
};

export default config;
