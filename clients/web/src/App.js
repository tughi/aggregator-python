import classNames from "classnames"
import { useEffect } from "react"
import { Reader } from "./reader/Reader"

export const App = () => {
   const pathname = window.location.pathname
   useEffect(() => {
      if (!pathname.startsWith('/reader/')) {
         window.history.replaceState({}, '', '/reader/all')
      }
   }, [pathname])

   return (
      <div className={classNames("App", navigator.maxTouchPoints > 0 ? "touch-mode" : "click-mode")}>
         <Reader />
      </div >
   )
}
