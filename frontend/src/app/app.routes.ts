import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () =>
      import('./pages/login/login.component').then((m) => m.LoginComponent),
  },
  {
    path: 'register',
    loadComponent: () =>
      import('./pages/register/register.component').then(
        (m) => m.RegisterComponent
      ),
  },
  {
    path: 'confirm',
    loadComponent: () =>
      import('./pages/confirm/confirm.component').then(
        (m) => m.ConfirmComponent
      ),
  },
  {
    path: '',
    canActivate: [authGuard],
    children: [
      {
        path: '',
        loadComponent: () =>
          import('./pages/home/home.component').then((m) => m.HomeComponent),
      },
      {
        path: 'video/:id',
        loadComponent: () =>
          import('./pages/player/player.component').then(
            (m) => m.PlayerComponent
          ),
      },
    ],
  },
  { path: '**', redirectTo: '' },
];
