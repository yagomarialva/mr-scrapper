import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-confirm',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="auth-page">
      <div class="auth-container glass-card">
        <div class="auth-logo">
          <span class="logo-icon">🎬</span>
          <h1 class="logo-text">Mr. Scrapper</h1>
        </div>

        @if (loading()) {
          <div class="confirm-status">
            <span class="spinner-lg"></span>
            <p>Verificando seu email...</p>
          </div>
        }

        @if (success()) {
          <div class="alert alert-success">
            ✅ {{ success() }}
          </div>
          <a routerLink="/login" class="btn btn-primary" style="width:100%;margin-top:16px;">
            Fazer Login
          </a>
        }

        @if (error()) {
          <div class="alert alert-error">
            ❌ {{ error() }}
          </div>
          <a routerLink="/login" class="btn btn-secondary" style="width:100%;margin-top:16px;">
            Voltar ao Login
          </a>
        }
      </div>
    </div>
  `,
  styles: [`
    .auth-page {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: var(--spacing-lg);
    }
    .auth-container {
      width: 100%;
      max-width: 440px;
      padding: var(--spacing-2xl);
      animation: fadeInScale 0.5s ease;
    }
    .auth-logo {
      text-align: center;
      margin-bottom: var(--spacing-xl);
    }
    .logo-icon {
      font-size: 3rem;
      display: block;
      margin-bottom: var(--spacing-sm);
    }
    .logo-text {
      font-size: 1.75rem;
      font-weight: 800;
      background: var(--accent-gradient);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }
    .confirm-status {
      text-align: center;
      color: var(--text-secondary);
    }
    .spinner-lg {
      display: inline-block;
      width: 40px;
      height: 40px;
      border: 3px solid rgba(255, 255, 255, 0.15);
      border-top-color: var(--accent-start);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
      margin-bottom: var(--spacing-md);
    }
    @keyframes spin { to { transform: rotate(360deg); } }
  `],
})
export class ConfirmComponent implements OnInit {
  loading = signal(true);
  success = signal<string | null>(null);
  error = signal<string | null>(null);

  constructor(
    private route: ActivatedRoute,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    const token = this.route.snapshot.queryParamMap.get('token');

    if (!token) {
      this.loading.set(false);
      this.error.set('Token de confirmação não encontrado.');
      return;
    }

    this.authService.confirmEmail(token).subscribe({
      next: (res) => {
        this.loading.set(false);
        this.success.set(res.message);
      },
      error: (err) => {
        this.loading.set(false);
        this.error.set(
          err.error?.detail || 'Falha ao confirmar email. Token inválido ou expirado.'
        );
      },
    });
  }
}
