import Aura from '@primeuix/themes/aura'
import PrimeVue from 'primevue/config'
import { createApp } from 'vue'
import rootComponent from './App.vue'

const primeVueOptions = {
  theme: {
    preset: Aura,
    options: {
      prefix: 'p',
    },
  },
}

async function bootstrap () {
  const app = createApp(rootComponent)
  app.use(PrimeVue, primeVueOptions)
  app.mount('#app')
}

bootstrap()
