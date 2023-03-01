import "./EntryViewer.scss"

import classNames from "classnames"
import { useCallback, useEffect, useRef } from "react"
import { ActionBar } from "./ActionBar"
import { useController } from "./Controller"
import { formatFullEntryTime } from "../utils/date"
import { range } from "../utils/array"

export const EntryViewer = () => {
   const { activeEntryIndex, setActiveEntryIndex, isViewerVisible, setIsViewerVisible, session } = useController()
   const { feedsById, entryIds, entries, toggleEntryReadState, toggleEntryStarState } = session
   const entriesLength = entries.length

   const activeEntry = entries[activeEntryIndex]

   useEffect(() => {
      if (isViewerVisible && activeEntry && activeEntry.readTime == null && activeEntry.keepTime == null) {
         toggleEntryReadState(activeEntry)
      }
   }, [isViewerVisible, activeEntry, toggleEntryReadState])

   const ref = useRef(null)
   useEffect(() => {
      const viewer = ref.current

      if (!viewer.closest('.App.touch-mode')) {
         return
      }

      const body = viewer.querySelector('.body')

      const TOUCH_STATE_DETECT = 1
      const TOUCH_STATE_DRAGGING = 1

      let touchState = null
      let touchDraggingDirection = 0
      let touchStartX = 0
      let touchStartY = 0
      let touchDeltaX = 0
      let touchDeltaY = 0

      let prevEntry = null
      let currEntry = null
      let nextEntry = null

      const touchStartListener = (event) => {
         prevEntry = body.querySelector('.entry.prev-1')
         currEntry = body.querySelector('.entry.active')
         nextEntry = body.querySelector('.entry.next-1')

         // TODO: ignore touch events if the touch target is inside of a scrollable container

         if (prevEntry || nextEntry) {
            touchState = TOUCH_STATE_DETECT
            touchStartX = event.touches[0].clientX
            touchStartY = event.touches[0].clientY
            touchDraggingDirection = 0
         } else {
            touchState = null
         }
      }

      const touchMoveListener = (event) => {
         const newTouchDeltaX = touchStartX - event.touches[0].clientX
         touchDraggingDirection = newTouchDeltaX - touchDeltaX
         touchDeltaX = newTouchDeltaX
         touchDeltaY = touchStartY - event.touches[0].clientY

         if (touchState === TOUCH_STATE_DETECT) {
            let touchAbsoluteDeltaX = Math.abs(touchDeltaX)
            let touchAbsoluteDeltaY = Math.abs(touchDeltaY)

            if (touchAbsoluteDeltaX < 5 && touchAbsoluteDeltaY < 5) {
               console.log('Movement too small for detection!')
            } else if (touchAbsoluteDeltaX > touchAbsoluteDeltaY) {
               touchState = TOUCH_STATE_DRAGGING
            } else {
               touchState = null
            }
         }

         if (touchState === TOUCH_STATE_DRAGGING) {
            event.preventDefault()

            if (touchDeltaX > 0) {
               if (nextEntry) {
                  nextEntry.style.left = `calc(100% + 1rem - ${touchDeltaX}px)`
                  nextEntry.style.transition = 'none'
               }

               currEntry.style.left = null
               currEntry.style.transition = null
            } else {
               if (prevEntry) {
                  currEntry.style.left = `${-touchDeltaX}px`
                  currEntry.style.transition = 'none'
               }

               if (nextEntry) {
                  nextEntry.style.left = null
                  nextEntry.style.transition = null
               }
            }
         }
      }

      const touchEndListener = (event) => {
         if (touchState === TOUCH_STATE_DRAGGING) {
            if (touchDeltaX > 0 && touchDraggingDirection > 0) {
               setActiveEntryIndex(activeEntryIndex => Math.min(activeEntryIndex + 1, entriesLength - 1))
            } else if (touchDeltaX < 0 && touchDraggingDirection < 0) {
               setActiveEntryIndex(activeEntryIndex => Math.max(activeEntryIndex - 1, 0))
            }

            if (prevEntry) {
               currEntry.style.left = null
               currEntry.style.transition = null
            }
            if (nextEntry) {
               nextEntry.style.left = null
               nextEntry.style.transition = null
            }
         }
      }

      body.addEventListener('touchstart', touchStartListener)
      body.addEventListener('touchmove', touchMoveListener)
      body.addEventListener('touchend', touchEndListener)

      return () => {
         body.removeEventListener('touchstart', touchStartListener)
         body.removeEventListener('touchmove', touchMoveListener)
         body.removeEventListener('touchend', touchEndListener)
      }
   }, [entriesLength, setActiveEntryIndex])

   return (
      <div ref={ref} className={classNames("EntryViewer", "content", { active: isViewerVisible })}>
         <div className="header">
            <ActionBar>
               <ActionBar.Action icon="close" onClick={() => setIsViewerVisible(false)} />
               {activeEntry && (
                  <>
                     <ActionBar.Title>
                        {activeEntryIndex + 1} / {entryIds.length}
                     </ActionBar.Title>
                     <ActionBar.Action icon="arrow-back" onClick={() => setActiveEntryIndex(activeEntryIndex => Math.max(activeEntryIndex - 1, 0))} disabled={activeEntryIndex <= 0} />
                     <ActionBar.Action icon="arrow-forward" onClick={() => setActiveEntryIndex(activeEntryIndex => Math.min(activeEntryIndex + 1, entriesLength - 1))} disabled={activeEntryIndex >= entriesLength - 1} />
                     <ActionBar.Action icon={activeEntry.starTime ? "star-on" : "star-off"} onClick={() => toggleEntryStarState(activeEntry)} />
                     <ActionBar.Action icon={activeEntry.keepTime ? "entry-pinned" : activeEntry.readTime ? "entry-done" : "entry-new"} active={!!activeEntry.keepTime} onClick={() => toggleEntryReadState(activeEntry)} />
                  </>
               )}
            </ActionBar>
         </div>
         <div className="body">
            {isViewerVisible && range(Math.max(0, activeEntryIndex - 2), Math.min(activeEntryIndex + 3, entriesLength)).map(entryIndex => {
               const entry = entries[entryIndex]
               let className = null
               if (activeEntryIndex > entryIndex) {
                  className = `prev-${activeEntryIndex - entryIndex}`
               } else if (activeEntryIndex < entryIndex) {
                  className = `next-${entryIndex - activeEntryIndex}`
               } else {
                  className = 'active'
               }
               return (
                  <Entry key={entry.id} className={className} entry={entry} feed={feedsById[entry.feedId]} />
               )
            })}
         </div>
      </div>
   )
}

const onLinkClick = event => {
   const element = event.target.closest('a')
   if (element) {
      event.preventDefault()
      const href = element.getAttribute('href')
      if (href) {
         window.open(href, '_blank', 'noopener noreferrer')
      }
   }
}

const Entry = ({ className, entry, feed }) => {
   const contentRef = useRef(null)
   const onContentRef = useCallback(node => {
      if (node) {
         node.addEventListener('click', onLinkClick)
      } else if (contentRef.current) {
         contentRef.current.removeEventListener('click', onLinkClick)
      }
      contentRef.current = node
   }, [])

   return (
      <div key={entry.id} className={classNames("entry", className)}>
         {entry && (
            <div ref={onContentRef} className="content">
               <div className="header">
                  <div className="source">
                     <span className="feed">{feed.userTitle || feed.title}</span>
                     {entry.author && (
                        <span className="author">{entry.author.name}</span>
                     )}
                  </div>
                  <h2><a className="title" href={entry.link}>{entry.title}</a></h2>
                  <div>
                     <span className="date" title={entry.publishText}>{formatFullEntryTime(entry.publishTime)}</span>
                  </div>
               </div>
               {((entry?.content.length && entry.content) || (entry.summary && [entry.summary]) || []).map((content, index) => (
                  <div key={index} dangerouslySetInnerHTML={{ __html: content.value }}></div>
               ))}
            </div>
         )}
      </div>
   )
}
