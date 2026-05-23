import { Injectable, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap, catchError, throwError } from 'rxjs';

export interface UserResponse {
  id: string;
  name: string;
  email: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface MessageResponse {
  message: string;
  detail?: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly API = '/api/auth';
  private readonly TOKEN_KEY = 'mr_scrapper_token';
  private readonly USER_KEY = 'mr_scrapper_user';

  /** Reactive auth state using Angular Signals */
  private _token = signal<string | null>(this.getStoredToken());
  private _user = signal<UserResponse | null>(this.getStoredUser());

  readonly isAuthenticated = computed(() => !!this._token());
  readonly currentUser = computed(() => this._user());
  readonly token = computed(() => this._token());

  constructor(
    private http: HttpClient,
    private router: Router
  ) {}

  // ── Public API ────────────────────────────────────────────────

  register(name: string, email: string, password: string): Observable<MessageResponse> {
    return this.http.post<MessageResponse>(`${this.API}/register`, {
      name,
      email,
      password,
    });
  }

  login(email: string, password: string): Observable<TokenResponse> {
    return this.http
      .post<TokenResponse>(`${this.API}/login`, { email, password })
      .pipe(
        tap((res) => {
          this.storeToken(res.access_token);
          this.fetchMe().subscribe();
        })
      );
  }

  confirmEmail(token: string): Observable<MessageResponse> {
    return this.http.get<MessageResponse>(`${this.API}/confirm/${token}`);
  }

  fetchMe(): Observable<UserResponse> {
    return this.http.get<UserResponse>(`${this.API}/me`).pipe(
      tap((user) => {
        this._user.set(user);
        localStorage.setItem(this.USER_KEY, JSON.stringify(user));
      }),
      catchError((err) => {
        this.logout();
        return throwError(() => err);
      })
    );
  }

  logout(): void {
    this._token.set(null);
    this._user.set(null);
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
    this.router.navigate(['/login']);
  }

  // ── Private Helpers ───────────────────────────────────────────

  private storeToken(token: string): void {
    this._token.set(token);
    localStorage.setItem(this.TOKEN_KEY, token);
  }

  private getStoredToken(): string | null {
    if (typeof localStorage === 'undefined') return null;
    return localStorage.getItem(this.TOKEN_KEY);
  }

  private getStoredUser(): UserResponse | null {
    if (typeof localStorage === 'undefined') return null;
    const raw = localStorage.getItem(this.USER_KEY);
    return raw ? JSON.parse(raw) : null;
  }
}
