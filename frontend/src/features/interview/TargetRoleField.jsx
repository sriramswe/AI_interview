import { useState } from 'react'

const TARGET_ROLES = [
  'Software Engineer',
  'Frontend Developer',
  'Backend Developer',
  'Full Stack Developer',
  'Mobile App Developer',
  'DevOps Engineer',
  'Cloud Engineer',
  'Cybersecurity Analyst',
  'QA Engineer',
  'Data Analyst',
  'Data Scientist',
  'Machine Learning Engineer',
  'AI Engineer',
  'Product Manager',
  'Project Manager',
  'Business Analyst',
  'UI/UX Designer',
  'Graphic Designer',
  'Digital Marketing Specialist',
  'Sales Representative',
  'Human Resources Manager',
  'Financial Analyst',
]

export default function TargetRoleField({
  value,
  onChange,
  autoFocus = false,
  required = false,
}) {
  const [customRoleSelected, setCustomRoleSelected] = useState(
    Boolean(value && !TARGET_ROLES.includes(value)),
  )
  const isCustomRole = customRoleSelected || Boolean(
    value && !TARGET_ROLES.includes(value),
  )

  const handleSelectionChange = (event) => {
    const selectedRole = event.target.value
    const isCustom = selectedRole === 'other'
    setCustomRoleSelected(isCustom)
    onChange(isCustom ? '' : selectedRole)
  }

  return (
    <>
      <label>
        Target role
        <select
          autoFocus={autoFocus}
          onChange={handleSelectionChange}
          required={required}
          value={isCustomRole ? 'other' : value}
        >
          <option disabled value="">Choose a target role</option>
          {TARGET_ROLES.map((role) => <option key={role} value={role}>{role}</option>)}
          <option value="other">Other</option>
        </select>
      </label>
      {isCustomRole && (
        <input
          aria-label="Enter your target role"
          maxLength={120}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Enter your target role"
          required={required}
          value={value}
        />
      )}
    </>
  )
}
