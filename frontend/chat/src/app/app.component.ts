import { Component, ViewChild, ElementRef, NgZone } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpEvent } from '@angular/common/http';
import { CardModule } from 'primeng/card';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { TagModule } from 'primeng/tag';
import { marked } from 'marked';
import { timeout, tap } from 'rxjs/operators';
import katex from 'katex';

interface Message {
    role: 'user' | 'assistant';
    content: string;
    image?: string;
    imageType?: string;
    sources?: string[];
    model?: string;
}

interface Chat {
    id: string;
    title: string;
    messages: Message[];
}

@Component({
    selector: 'app-root',
    standalone: true,
    imports: [
        CommonModule,
        FormsModule,
        CardModule,
        ButtonModule,
        InputTextModule,
        ProgressSpinnerModule,
        TagModule
    ],
    templateUrl: './app.component.html',
    styleUrl: './app.component.css'
})

export class AppComponent {
    chats: Chat[] = [];
    currentChatId: string | null = null;
    question: string = '';
    loading: boolean = false;
    questionCount: number = 0;
    questionLimit: number = 10;
    clientId = '552296794218-rs88k3i25s97snuomulfnurpfd36bct6.apps.googleusercontent.com';
    idToken: string | null = null;
    userEmail: string | null = null;

    loadingMessages: Record<string, string> = {
        building_chain: 'Preparing the prompt...',
        invoking_question: 'Sending the question to the model...',
        model_used: 'Waiting for model response...',
        retrying_query_translation: 'Retrying with broader retrieval...',
        query_translation_used: 'Using translated query search...',
        fallback_model: 'Retrying with fallback model...',
        skipping_model: 'Skipping exhausted model...',
    };
    currentLoadingMessage: string = '';
    copiedMessages = new Set<number>();
    selectedImage: string | null = null;
    selectedImageType: string | null = null;

    constructor(private http: HttpClient, private ngZone: NgZone) {
        this.createNewChat();
    }

    ngOnInit() {
        const initGoogle = () => {
            if ((window as any).google) {
                (window as any).google.accounts.id.initialize({
                    client_id: this.clientId,
                    callback: (response: any) => this.handleGoogleSignIn(response),
                    hosted_domain: 'rice.edu'
                });
                (window as any).google.accounts.id.prompt();

                setTimeout(() => {
                    (window as any).google.accounts.id.renderButton(
                        document.getElementById('google-signin-button'),
                        { theme: 'outline', size: 'large', text: 'signin_with' }
                    );
                }, 100);
            } else {
                setTimeout(initGoogle, 100);
            }
        };
        initGoogle();
    }

    // Chat

    get currentChat(): Chat | null {
        return this.chats.find(c => c.id === this.currentChatId) || null;
    }

    get messages(): Message[] {
        return this.currentChat?.messages || [];
    }

    createNewChat() {
        const chat: Chat = {
            id: crypto.randomUUID(),
            title: 'New Chat',
            messages: []
        };
        this.chats.unshift(chat);  
        this.currentChatId = chat.id;
    }

    switchChat(chatId: string) {
        this.currentChatId = chatId;
    }

    deleteChat(chatId: string, event: Event) {
        event.stopPropagation();  // prevent switchChat from firing
        this.chats = this.chats.filter(c => c.id !== chatId);
        if (this.currentChatId === chatId) {
            if (this.chats.length > 0) {
                this.currentChatId = this.chats[0].id;
            } else {
                this.createNewChat();
            }
        }
    }

    onPaste(event: ClipboardEvent) {
        const items = event.clipboardData?.items;
        if (!items) return;
        for (const item of Array.from(items))
        {
            if (item.type.startsWith('image/')) {
                this.selectedImageType = item.type;
                const file = item.getAsFile()
                if (!file) return;
                const reader = new FileReader();
                reader.onload = () => {
                    this.selectedImage = (reader.result as string).split(',')[1];
                }
                reader.readAsDataURL(file);
            }
        }
    }

    clearImage() {
        this.selectedImage = null;
        this.selectedImageType = null;
    }

    // Utils

    renderMarkdown(text: string): string {
        let html = marked(text) as string;
        
        // Render block math: $$...$$
        html = html.replace(/\$\$([^$]+)\$\$/g, (_, math) => {
            try {
                return katex.renderToString(math, { displayMode: true });
            } catch { return math; }
        });
        
        // Render inline math: $...$
        html = html.replace(/\$([^$\n]+)\$/g, (_, math) => {
            try {
                return katex.renderToString(math, { displayMode: false });
            } catch { return math; }
        });
        
        return html;
    }
    
    @ViewChild('scrollAnchor') scrollAnchor!: ElementRef;

    scrollToBottom() {
        setTimeout(() => {
            this.scrollAnchor?.nativeElement?.scrollIntoView({ behavior: 'smooth' });
        }, 50);
    }

    copyMessage(text: string, index: number) {
        navigator.clipboard.writeText(text).then(() => {
            this.copiedMessages.add(index);
            setTimeout(() => this.copiedMessages.delete(index), 2000);
        });
    }

    updateLoadingMessage(step: string) {
        this.currentLoadingMessage = this.loadingMessages[step] || 'Loading...';
    }
    
    stopLoadingMessages() {
        this.currentLoadingMessage = '';
    }

    getDots() {
        return Array.from({length: this.questionLimit}, (_, i) => ({
            used: i >= (this.questionLimit - this.questionCount)
        }));
    }

    // Ask 

    ask() {
        if (!this.question.trim() || this.loading) return;
        if (this.questionCount >= this.questionLimit) return;
        if (!this.currentChat) return;

        const userMessage: Message = {
            role: 'user',
            content: this.question,
            image: this.selectedImage || undefined,
            imageType: this.selectedImageType || undefined
        };

        this.currentChat.messages.push(userMessage);

        if (this.currentChat.messages.length === 1) {
            this.currentChat.title = this.question.length > 30
                ? this.question.substring(0, 30) + '...'
                : this.question;
        }

        this.scrollToBottom();
        const currentQuestion = this.question;
        const currentImage = this.selectedImage;
        const currentImageType = this.selectedImageType;
        this.question = '';
        this.loading = true;
        this.questionCount++;
        this.updateLoadingMessage('building_chain');
        
        const history = this.currentChat.messages.slice(0, -1).map(m => ({
            role: m.role,
            content: m.content
        }));

        const controller = new AbortController();
        fetch('http://localhost:8000/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.idToken}`},
            body: JSON.stringify({ question: currentQuestion, history: history, image: currentImage, imageType: currentImageType }),
            signal: controller.signal
        }).then(async response => {
            if (!response.body) {
                throw new Error('ERROR: No response body');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            const processEvent = (eventText: string) => {
                const lines = eventText.split('\n');
                let event = 'message';
                let data = '';

                for (const line of lines) {
                    if (line.startsWith('event:')) {
                        event = line.replace('event:', '').trim();
                    } else if (line.startsWith('data:')) {
                        data += line.replace('data:', '').trim();
                    }
                }
                if (!data) return;

                const payload = JSON.parse(data);
                if (event === 'progress') {
                    this.updateLoadingMessage(payload.stage);
                } else if (event === 'answer') {
                    this.currentChat!.messages.push({
                        role: 'assistant',
                        content: payload.answer,
                        sources: payload.sources,
                        model: payload.model_used,
                    });
                } else if (event === 'error') {
                    this.currentChat!.messages.push({
                        role: 'assistant',
                        content: payload.message || 'Something went wrong. Please try again.',
                        sources: [],
                    });
                    this.loading = false;
                    this.stopLoadingMessages();
                    this.scrollToBottom();
                } else if (event === 'done') {
                    this.loading = false;
                    this.stopLoadingMessages();
                    this.scrollToBottom();
                }
            };

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const parts = buffer.split('\n\n');
                buffer = parts.pop() || '';
                for (const part of parts) {
                    if (part.trim()) {
                        processEvent(part.trim());
                    }
                }
            }
            if (buffer.trim()) {
                processEvent(buffer.trim());
            }
        }).catch(err => {
            this.currentChat!.messages.push({
                role: 'assistant',
                content: err.name === 'AbortError'
                    ? 'The request was aborted.'
                    : 'Something went wrong. Please try again.',
                sources: [],
            });
            this.loading = false;
            this.stopLoadingMessages();
            this.scrollToBottom();
        });
    }

    onEnter(event: KeyboardEvent) {
        if (event.key === 'Enter') {
            this.ask()
            this.clearImage();
        }
    }

    handleGoogleSignIn(response: any) {
        this.ngZone.run(() => {
            this.idToken = response.credential;
            const payload = JSON.parse(atob(response.credential.split('.')[1]));
            this.userEmail = payload.email;
            console.log('Signed in as:', this.userEmail);
        });
    }
}