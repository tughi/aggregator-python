import "./ActionBar.scss"

import classNames from "classnames"

export const ActionBar = ({ children }) => (
   <div className="ActionBar">
      <div className="bar">
         {children}
      </div>
   </div>
)

const Action = ({ icon, onClick }) => (
   <button className={classNames("action", icon)} onClick={onClick} />
)

const Title = ({ children }) => (
   <div className="title">
      {children}
   </div>
)

Object.defineProperty(ActionBar, 'Action', { value: Action })
Object.defineProperty(ActionBar, 'Title', { value: Title })
