import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './register.component.html',
  styleUrl: './register.component.css',
})
export class RegisterComponent {
  name = '';
  email = '';
  password = '';
  confirmPassword = '';
  loading = signal(false);
  error = signal<string | null>(null);
  success = signal<string | null>(null);

  constructor(
    private authService: AuthService,
    private router: Router
  ) {
    if (this.authService.isAuthenticated()) {
      this.router.navigate(['/']);
    }
  }

  onSubmit(): void {
    this.error.set(null);
    this.success.set(null);

    if (!this.name || !this.email || !this.password || !this.confirmPassword) {
      this.error.set('Preencha todos os campos.');
      return;
    }

    if (this.password.length < 8) {
      this.error.set('A senha deve ter pelo menos 8 caracteres.');
      return;
    }

    if (this.password !== this.confirmPassword) {
      this.error.set('As senhas não coincidem.');
      return;
    }

    this.loading.set(true);

    this.authService.register(this.name, this.email, this.password).subscribe({
      next: (res) => {
        this.loading.set(false);
        this.success.set(res.message + (res.detail ? ' ' + res.detail : ''));
      },
      error: (err) => {
        this.loading.set(false);
        this.error.set(
          err.error?.detail || 'Erro ao criar conta. Tente novamente.'
        );
      },
    });
  }
}
