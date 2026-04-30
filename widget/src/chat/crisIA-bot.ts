import { LitElement, html, unsafeCSS } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

import widgetStyles from '../styles/stylesChat.css?inline';

// 1. INTERFACES (Seguridad de tipos)
interface ChatMessage {
  sender: 'bot' | 'user';
  text: string;
}

// 2. REGISTRO DEL WEB COMPONENT MEDIANTE DECORADORES
@customElement('accesspark-bot')
export class AccessParkBot extends LitElement {

  // 3. DEFINICIÓN DE PROPIEDADES (Lo que el cliente pasa por HTML)
  @property({ type: String, attribute: 'client-id' })
  clientId: string = 'default';

  @property({ type: String, attribute: 'theme-color' })
  themeColor: string = 'rgb(0, 86, 179)';

  @property({ type: String, attribute: 'font-family' })
  fontFamily: string = 'Segoe UI, sans-serif';

  // 4. DEFINICIÓN DE ESTADOS INTERNOS (Privados)
  @state()
  private isOpen: boolean = false;

  @state()
  private messages: ChatMessage[] = [
    { sender: 'bot', text: '¡Hola! Bienvenido. ¿En qué te puedo ayudar hoy?' }
  ];

  @state()
  private inputText: string = '';

  // --- VARIABLES PARA EL ARRASTRE ---
  @state() private translateX: number = 0; 
  @state() private translateY: number = 0; 
  @state() private isTyping: boolean = false; 

  // Variables de control interno
  private isDragging: boolean = false;
  private initialX: number = 0;
  private initialY: number = 0;

  connectedCallback() {
    super.connectedCallback();
    window.addEventListener('resize', this.handleResize);
  }

  disconnectedCallback() {
    window.removeEventListener('resize', this.handleResize);
    super.disconnectedCallback();
  }

  private handleResize = () => {
    this.clampPosition();
  };

  private clampPosition(): void {
    const chatWidth = this.isOpen ? Math.min(350, window.innerWidth - 40) : 0;
    const chatHeight = this.isOpen ? Math.min(500, window.innerHeight - 120) : 0;

    const maxRightDrag = 0;
    const maxDownDrag = 0;
    const maxLeftDrag = -(window.innerWidth - Math.max(60, chatWidth) - 40);
    const maxUpDrag = -(window.innerHeight - Math.max(60, chatHeight) - 90);

    const effectiveMaxLeft = Math.min(maxLeftDrag, 0);
    const effectiveMaxUp = Math.min(maxUpDrag, 0);

    this.translateX = Math.max(effectiveMaxLeft, Math.min(this.translateX, maxRightDrag));
    this.translateY = Math.max(effectiveMaxUp, Math.min(this.translateY, maxDownDrag));
  }

  // --- NUEVA LÓGICA: GENERACIÓN DE SESSION ID ---
  // Genera un ID único temporal y lo guarda en el navegador del usuario
  private getSessionId(): string {
    let sessionId = sessionStorage.getItem('chat_session_id');
    if (!sessionId) {
      // Crea un ID aleatorio (ej. sess_1a2b3c4d)
      sessionId = 'sess_' + Math.random().toString(36).substring(2, 15);
      sessionStorage.setItem('chat_session_id', sessionId);
    }
    return sessionId;
  }

  // 5. ESTILOS BLINDADOS Y RESPONSIVOS
  static styles = unsafeCSS(widgetStyles);

  // --- LÓGICA DE ARRASTRE ---
  private dragStart(e: PointerEvent): void {
    this.initialX = e.clientX - this.translateX;
    this.initialY = e.clientY - this.translateY;
    this.isDragging = true;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  }

  private drag(e: PointerEvent): void {
    if (!this.isDragging) return;
    e.preventDefault();
    this.translateX = e.clientX - this.initialX;
    this.translateY = e.clientY - this.initialY;
    this.clampPosition();
  }

  private dragEnd(e: PointerEvent): void {
    this.isDragging = false;
    (e.target as HTMLElement).releasePointerCapture(e.pointerId);
  }

  // 6. LÓGICA DEL COMPONENTE
  private toggleChat(): void {
    this.isOpen = !this.isOpen;
    this.clampPosition();
  }

  private handleInput(e: Event): void {
    const input = e.target as HTMLInputElement; 
    this.inputText = input.value;
  }

  private handleKeyPress(e: KeyboardEvent): void {
    if (e.key === 'Enter') {
      this.sendMessage();
    }
  }

  private async sendMessage(textToSend: string = this.inputText): Promise<void> {
    if (!textToSend.trim()) return;

    // 1. Agregamos el mensaje del usuario a la pantalla
    this.messages = [...this.messages, { sender: 'user', text: textToSend }];
    this.inputText = ''; 
    
    // 2. Encendemos el indicador de escritura
    this.isTyping = true;
    
    try {
      // 3. Nos conectamos a FastAPI enviando el Client ID y el Session ID
      const response = await fetch('http://127.0.0.1:8000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          client_id: this.clientId, 
          session_id: this.getSessionId(), // <-- AQUÍ SE ENVÍA EL ID A REDIS
          text: textToSend
        })
      });

      if (!response.ok) {
        throw new Error(`Error HTTP: ${response.status}`);
      }

      const data = await response.json();

      // 4. Mostramos la respuesta de la IA
      this.messages = [...this.messages, {
        sender: 'bot',
        text: data.response
      }];

    } catch (error) {
      console.error("Error conectando con el backend:", error);
      this.messages = [...this.messages, {
        sender: 'bot',
        text: 'Lo siento, mis sistemas están desconectados en este momento. Por favor intenta más tarde.'
      }];
    } finally {
      // 5. Apagamos el indicador de escritura
      this.isTyping = false;
    }
  }

  private sendOption(optionText: string): void {
    this.sendMessage(optionText);
  }

  // 7. RENDERIZADO HTML
  render() {
    const dynamicStyles = html`
      <style>
        :host { 
          --bot-theme-color: ${this.themeColor};
          --bot-font-family: ${this.fontFamily};
        }
        .launcher, .header { cursor: grab; }
        .launcher:active, .header:active { cursor: grabbing; }
      </style>
    `;

    return html`
      ${dynamicStyles}
      <div class="widget-container" style="transform: translate3d(${this.translateX}px, ${this.translateY}px, 0);">
      <button 
      class="launcher" 
      @click=${this.toggleChat}
      @pointerdown=${this.dragStart}
      @pointermove=${this.drag}
      @pointerup=${this.dragEnd}
      @pointercancel=${this.dragEnd}>
        ${this.isOpen ? '✕' : '💬'}
      </button>

      ${this.isOpen ? html`
        <div class="chat-window">
          <div 
          class="header"
          @pointerdown=${this.dragStart}
          @pointermove=${this.drag}
          @pointerup=${this.dragEnd}
          @pointercancel=${this.dragEnd}
          >
            Habla con crisIA
          </div>

          <div class="messages">
            ${this.messages.map(msg => html`
              <div class="message ${msg.sender}">${msg.text}</div>
            `)}
            
            ${this.isTyping ? html`
              <div class="message bot typing">
                <div class="dot">...</div>
              </div>
            ` : ''}
            
            ${this.messages.length === 1 && !this.isTyping ? html`
              <div class="options-container">
                <button class="option-btn" @click=${() => this.sendOption('hola deseo Comprar/Productos')}>Comprar/Productos</button>
                <button class="option-btn" @click=${() => this.sendOption('hola deseo Trabajar con accesspark')}>Trabajar con nosotros</button>
                <button class="option-btn" @click=${() => this.sendOption('hola deseo recibir Soporte Técnico')}>Soporte Técnico</button>
              </div>
            ` : ''}
          </div>
          <div class="input-area">
            <input 
              type="text" 
              .value=${this.inputText} 
              @input=${this.handleInput} 
              @keypress=${this.handleKeyPress}
              placeholder="Escribe tu mensaje..."
            />
            <button class="send" @click=${() => this.sendMessage()}>➤</button>
          </div>
        </div>
      ` : ''}
    </div>  
    `;
  }
}