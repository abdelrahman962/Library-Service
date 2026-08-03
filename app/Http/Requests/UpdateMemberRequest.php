<?php

namespace App\Http\Requests;

use Illuminate\Contracts\Validation\ValidationRule;
use Illuminate\Foundation\Http\FormRequest;

class UpdateMemberRequest extends FormRequest
{
    /**
     * Determine if the user is authorized to make this request.
     */
    public function authorize(): bool
    {
        return true;
    }

    /**
     * Get the validation rules that apply to the request.
     *
     * @return array<string, ValidationRule|array<mixed>|string>
     */
    public function rules(): array
    {
        return [
            //
            'name' => 'required|string|max:255',

            'email' => 'required|email|unique:members,email,' . $this->member->id,

        ];
    }

    public function messages(): array
    {
        return [

            'name.required' => 'Member name is required.',

            'email.required' => 'Email is required.',

            'email.email' => 'Please enter a valid email address.',

            'email.unique' => 'This email already exists.',

        ];
    }
}
