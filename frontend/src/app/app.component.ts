import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { CommonModule } from '@angular/common';
import { ModalComponent } from './shared/components/modal/modal.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, CommonModule, ModalComponent],
  template: `<router-outlet /><app-modal></app-modal>`,
  styles: [
    `
      :host {
        display: block;
        position: relative;
        z-index: 1;
        min-height: 100vh;
      }
    `,
  ],
})
export class AppComponent {}
