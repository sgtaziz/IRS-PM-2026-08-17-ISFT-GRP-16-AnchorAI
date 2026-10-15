// Mirrors anchorai/auth/schemas.py.
export type Role = 'staff' | 'manager' | 'admin'

export interface UserOut {
  id: number
  username: string
  role: Role
  full_name: string
  is_active: boolean
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: UserOut
}
