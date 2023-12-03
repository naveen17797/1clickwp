import {Component, EventEmitter, Input, Output} from '@angular/core';
import {FormGroup} from "@angular/forms";

@Component({
  selector: 'app-create-form',
  templateUrl: './create-form.component.html',
  styleUrls: ['./create-form.component.less']
})
export class CreateFormComponent {

  @Input()
  siteForm: FormGroup | undefined

  @Output()
  onSubmitted:EventEmitter<any> = new EventEmitter<any>()

}
