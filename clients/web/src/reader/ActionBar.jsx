import "./ActionBar.scss"

import classNames from "classnames"

export const ActionBar = ({ children }) => (
   <div className="ActionBar">
      <div className="bar">
         {children}
      </div>
   </div>
)

const Action = ({ icon, active, onClick, disabled }) => (
   <button className={classNames("action", { active }, icon)} onClick={onClick} disabled={disabled} />
)

const Count = ({ children }) => (
   <div className="count">
      {children}
   </div>
)

const Title = ({ children }) => (
   <div className="title">
      {children}
   </div>
)

Object.defineProperty(ActionBar, 'Action', { value: Action })
Object.defineProperty(ActionBar, 'Count', { value: Count })
Object.defineProperty(ActionBar, 'Title', { value: Title })
