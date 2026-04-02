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
    messages: Message[] = [];
    question: string = '';
    loading: boolean = false;
    
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

    constructor(private http: HttpClient) {}

    renderMarkdown(text: string): string {
        return marked(text) as string;
    }
    
    @ViewChild('scrollAnchor') scrollAnchor!: ElementRef;

    scrollToBottom() {
        setTimeout(() => {
            this.scrollAnchor.nativeElement.scrollIntoView({ behavior: 'smooth' });
        }, 50);
    }

    ask() {
        if (!this.question.trim() || this.loading) return;

        const userMessage: Message = {
            role: 'user',
            content: this.question
        };

        this.messages.push(userMessage);
        this.scrollToBottom();
        const currentQuestion = this.question;
        this.question = '';
        this.loading = true;
        this.startLoadingMessages();
        
        this.http.post<{ answer: string, sources: string[] }>(
            'http://localhost:8000/query',
            { question: currentQuestion}
        ).pipe(timeout(60000))
        .subscribe({
            next: (response) => {
                this.messages.push({
                    role: 'assistant',
                    content: response.answer,
                    sources: response.sources
                });
                this.loading = false;
                this.stopLoadingMessages();
                this.scrollToBottom();
            },
            error: (err) => {
                this.messages.push({
                    role: 'assistant',
                    content: 'Something went wrong. Please try again.',
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
}