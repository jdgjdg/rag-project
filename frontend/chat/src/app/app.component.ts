import { Component, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { CardModule } from 'primeng/card';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { TagModule } from 'primeng/tag';
import { marked } from 'marked';
import { timeout } from 'rxjs/operators';

interface Message {
    role: 'user' | 'assistant';
    content: string;
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
    
    loadingMessages = [
        'Searching lecture notes...',
        'Retrieving relevant chunks...',
        'Generating answer...',
        'Consulting the database...',
        'Almost there...'
    ];
    currentLoadingMessage: string = '';
    loadingInterval: any = null;
    copiedMessages = new Set<number>();

    constructor(private http: HttpClient) {
        this.createNewChat();
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

    // Utils

    renderMarkdown(text: string): string {
        return marked(text) as string;
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

    startLoadingMessages() {
        let index = 0;
        this.currentLoadingMessage = this.loadingMessages[0];
        this.loadingInterval = setInterval(() => {
            index = (index + 1) % this.loadingMessages.length;
            this.currentLoadingMessage = this.loadingMessages[index];
        }, 4000);
    }
    
    stopLoadingMessages() {
        if (this.loadingInterval) {
            clearInterval(this.loadingInterval);
            this.loadingInterval = null;
        }
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
            content: this.question
        };

        this.currentChat.messages.push(userMessage);

        if (this.currentChat.messages.length === 1) {
            this.currentChat.title = this.question.length > 30
                ? this.question.substring(0, 30) + '...'
                : this.question;
        }

        this.scrollToBottom();
        const currentQuestion = this.question;
        this.question = '';
        this.loading = true;
        this.questionCount++;
        this.startLoadingMessages();
        
        const history = this.currentChat.messages.slice(0, -1).map(m => ({
            role: m.role,
            content: m.content
        }));

        this.http.post<{ answer: string, sources: string[], model_used: string}>(
            'http://localhost:8000/query',
            { question: currentQuestion, history: history}
        ).pipe(timeout(60000))
        .subscribe({
            next: (response) => {
                this.currentChat!.messages.push({
                    role: 'assistant',
                    content: response.answer,
                    sources: response.sources, 
                    model: response.model_used
                });
                this.loading = false;
                this.stopLoadingMessages();
                this.scrollToBottom();
            },
            error: (err) => {
                this.currentChat!.messages.push({
                    role: 'assistant',
                    content: err.name === 'TimeoutError'
                        ? 'The request timed out. Please try again.'
                        : 'Something went wrong. Please try again.',
                    sources: []    
                });
                this.loading = false;
                this.stopLoadingMessages();
                this.scrollToBottom();
            }
        });
    }

    onEnter(event: KeyboardEvent) {
        if (event.key === 'Enter') this.ask();
    }
}