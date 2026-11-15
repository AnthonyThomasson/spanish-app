import basicSsl from '@vitejs/plugin-basic-ssl';
import { createReadStream, existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { defineConfig } from 'vite';

const vocabPath = resolve(__dirname, 'data/vocab.json');

export default defineConfig(({ mode }) => ({
  plugins: [
    ...(mode === 'phone' ? [basicSsl()] : []),
    {
      name: 'local-vocabulary',
      configureServer(server) {
        server.middlewares.use('/data/vocab.json', (_request, response) => {
          if (!existsSync(vocabPath)) {
            response.statusCode = 404;
            response.end('Vocabulary data has not been generated.');
            return;
          }
          response.setHeader('Content-Type', 'application/json; charset=utf-8');
          createReadStream(vocabPath).pipe(response);
        });
      },
      generateBundle() {
        if (existsSync(vocabPath)) {
          this.emitFile({
            type: 'asset',
            fileName: 'data/vocab.json',
            source: readFileSync(vocabPath),
          });
        }
      },
    },
  ],
}));
