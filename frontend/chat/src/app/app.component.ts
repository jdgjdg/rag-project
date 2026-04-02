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

        this.http.post<{ answer: string, sources: string[] }>(
            'http://localhost:8000/query',
            { question: currentQuestion}
        ).subscribe({
            next: (response) => {
                this.messages.push({
                    role: 'assistant',
                    content: response.answer,
                    sources: response.sources
                });
                this.loading = false;
                this.scrollToBottom();
            },
            error: (err) => {
                this.messages.push({
                    role: 'assistant',
                    content: 'Something went wrong. Please try again.',
                    sources: []
                });
                this.loading = false;
                this.scrollToBottom();
            }
        });
    }

    onEnter(event: KeyboardEvent) {
        if (event.key === 'Enter') this.ask();
    }
}